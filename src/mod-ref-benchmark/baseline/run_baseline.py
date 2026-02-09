from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import shutil
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent  # src/mod-ref-benchmark
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from llm_client import LLMClient, LLMConfig  


DEFAULT_MODEL = "gpt-5.1-codex-max"


def load_verify_func(unit_test_path: Path):
    """Dynamically load the verification function from a CR's unit_test.py file."""
    spec = importlib.util.spec_from_file_location("verify", unit_test_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load unit test module from {unit_test_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_funcs = [getattr(module, f) for f in dir(module) if f.endswith("_verify_func")]
    if not verify_funcs:
        raise ValueError(f"No *_verify_func found in {unit_test_path}")
    return verify_funcs[0]


def extract_output_keys(ref_sol_format: dict) -> list[str]:
    """
    ref_sol_format uses placeholder keys like 'var1'. The real output keys are
    embedded as backtick-quoted identifiers in each entry's 'descr' field.
    """
    import re

    keys: list[str] = []
    for _, spec in (ref_sol_format or {}).items():
        descr = (spec or {}).get("descr", "") or ""
        m = re.search(r"`([^`]+)`", descr)
        if not m:
            continue
        name = m.group(1).strip()
        if name.endswith(":"):
            name = name[:-1].strip()
        if name and name not in keys:
            keys.append(name)
    return keys


def build_single_shot_prompt(
    *,
    base_nl_description: str,
    base_reference_code: str,
    cr_desc: dict[str, Any],
    expected_output_keys: list[str],
) -> str:
    cr_text = cr_desc.get("content", "")
    value_info = cr_desc.get("value_info", [])
    ref_sol_format = cr_desc.get("ref_sol_format", {})
    prob_type = cr_desc.get("prob_type", "")

    return f"""
You are a CPMPy modeling assistant.

Task: Modify/extend the given *base* CPMPy reference model to implement the Change Request (CR), and output a COMPLETE, EXECUTABLE Python script.

This is a single-shot generation: you must do everything in one pass.

Inputs you can rely on at runtime:
- A file named input_data.json in the same directory as the generated script.

Requirements (very important):
- Use CPMPy (cpmpy) and json for I/O. Only use other standard libs if truly necessary.
- Load ALL numeric parameters ONLY from input_data.json. Do NOT hard-code instance data.
- Implement the CR precisely while preserving unrelated base constraints.
- The script must be self-contained: do NOT import local project files (e.g., reference_model.py). Copy/adapt any needed code directly.
- Solve the model (satisfaction or optimization as appropriate).
- Print EXACTLY ONE JSON object to stdout using print(json.dumps(...)).

CRITICAL INSTRUCTION ABOUT OUTPUT KEYS:
- In ref_sol_format, keys like "var1", "var2", ... are placeholders.
- The REAL output keys are the backtick-quoted identifiers inside each ref_sol_format[*].descr.
- For this CR, you MUST output a JSON dict with the following top-level keys:
  {expected_output_keys}

Return format:
- Output ONLY the Python code (no markdown, no backticks, no surrounding text).

Base problem description (NL):
{base_nl_description}

Change Request:
{cr_text}

Parameter description (value_info):
{json.dumps(value_info, indent=2)}

Expected output format (ref_sol_format) [placeholders like var1 are NOT real keys]:
{json.dumps(ref_sol_format, indent=2)}

Problem type hint (prob_type):
{prob_type}

Base CPMPy reference model code:
{base_reference_code}
"""


def build_code_schema() -> dict[str, Any]:
    """Structured output schema for returning Python code from the LLM."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "python_code": {
                "type": "string",
                "description": "A complete Python script (CPMPy) that reads input_data.json, solves the CR, and prints JSON.",
            }
        },
        "required": ["python_code"],
    }


def run_python_script(*, script_path: Path, cwd: Path, timeout: int | None = None) -> tuple[dict[str, Any] | None, str, str, int]:
    """
    Run a python script in a subprocess, returning:
      (parsed_json_or_none, stdout, stderr, returncode)
    """
    result = subprocess.run(
        [sys.executable, script_path.name],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0:
        return None, stdout, stderr, int(result.returncode)

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None, stdout, stderr, int(result.returncode)

    return parsed, stdout, stderr, int(result.returncode)


def is_unit_test_pass(verify_result: Any) -> bool:
    if verify_result == "pass":
        return True
    if isinstance(verify_result, (list, tuple)) and verify_result and verify_result[0] == "pass":
        return True
    return False


@dataclass
class CasePaths:
    case_dir: Path
    generated_model_path: Path
    prompt_path: Path
    llm_response_path: Path
    exec_log_path: Path
    unit_test_log_path: Path
    result_path: Path


def prepare_case_dir(*, output_root: Path, problem: str, cr: str, timestamp: str) -> CasePaths:
    case_dir = output_root / problem / cr / timestamp
    case_dir.mkdir(parents=True, exist_ok=True)
    return CasePaths(
        case_dir=case_dir,
        generated_model_path=case_dir / "generated_model.py",
        prompt_path=case_dir / "prompt.txt",
        llm_response_path=case_dir / "llm_response.json",
        exec_log_path=case_dir / "execution.json",
        unit_test_log_path=case_dir / "unit_test.json",
        result_path=case_dir / "result.json",
    )


def run_single_case(
    *,
    problem_dir: Path,
    cr_dir: Path,
    llm: LLMClient,
    output_root: Path,
    timeout: int | None,
) -> dict[str, Any]:
    problem = problem_dir.name
    cr = cr_dir.name
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    paths = prepare_case_dir(output_root=output_root, problem=problem, cr=cr, timestamp=timestamp)

    base_dir = problem_dir / "base"
    base_desc_path = base_dir / "problem_desc.txt"
    base_model_path = base_dir / "reference_model.py"
    cr_desc_path = cr_dir / "desc.json"
    cr_input_path = cr_dir / "input_data.json"
    cr_unit_test_path = cr_dir / "unit_test.py"

    missing = [p for p in [base_desc_path, base_model_path, cr_desc_path, cr_input_path, cr_unit_test_path] if not p.exists()]
    if missing:
        return {
            "problem": problem,
            "cr": cr,
            "status": "skipped",
            "error": f"Missing required files: {[str(p) for p in missing]}",
        }

    base_nl_description = base_desc_path.read_text()
    base_reference_code = base_model_path.read_text()
    cr_desc = json.loads(cr_desc_path.read_text())

    expected_output_keys = extract_output_keys(cr_desc.get("ref_sol_format", {}))
    prompt = build_single_shot_prompt(
        base_nl_description=base_nl_description,
        base_reference_code=base_reference_code,
        cr_desc=cr_desc,
        expected_output_keys=expected_output_keys,
    )

    # Persist prompt for reproducibility/debugging.
    paths.prompt_path.write_text(prompt)

    schema = build_code_schema()
    llm_raw: dict[str, Any] | None = None
    code: str | None = None
    generation_error: str | None = None
    try:
        llm_raw = llm.generate_json(
            prompt=prompt,
            schema=schema,
            schema_name="baseline_code",
            system="Return JSON with a single key 'python_code'. The value must be a complete Python script. No markdown.",
        )
        code = (llm_raw or {}).get("python_code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("LLM returned empty python_code")
    except Exception as e:
        generation_error = str(e)

    # Save LLM response (even if partially available).
    paths.llm_response_path.write_text(json.dumps({"llm_raw": llm_raw, "error": generation_error}, indent=2))

    if generation_error:
        result = {
            "problem": problem,
            "cr": cr,
            "status": "fail",
            "stage": "generation",
            "error": generation_error,
            "case_dir": str(paths.case_dir),
            "prompt_path": str(paths.prompt_path),
            "llm_response_path": str(paths.llm_response_path),
        }
        paths.result_path.write_text(json.dumps(result, indent=2))
        return result

    assert code is not None

    # Write model + copy input_data.json into the case dir so execution uses relative paths.
    paths.generated_model_path.write_text(code)
    shutil.copy2(cr_input_path, paths.case_dir / "input_data.json")

    # Execute generated code.
    model_output, stdout, stderr, returncode = run_python_script(
        script_path=paths.generated_model_path,
        cwd=paths.case_dir,
        timeout=timeout,
    )
    exec_ok = model_output is not None
    exec_error: str | None = None
    if not exec_ok:
        if returncode != 0:
            exec_error = f"Non-zero exit code {returncode}."
        else:
            exec_error = "Stdout was not valid JSON."

    exec_log = {
        "exec_ok": exec_ok,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "parsed_json": model_output,
        "exec_error": exec_error,
    }
    paths.exec_log_path.write_text(json.dumps(exec_log, indent=2))

    if not exec_ok:
        result = {
            "problem": problem,
            "cr": cr,
            "status": "fail",
            "stage": "execution",
            "exec_error": exec_error,
            "case_dir": str(paths.case_dir),
            "generated_model_path": str(paths.generated_model_path),
            "execution_log_path": str(paths.exec_log_path),
            "prompt_path": str(paths.prompt_path),
            "llm_response_path": str(paths.llm_response_path),
        }
        paths.result_path.write_text(json.dumps(result, indent=2))
        return result

    # Run unit test.
    unit_test_pass = False
    unit_test_result: Any = None
    unit_test_error: str | None = None
    try:
        verify_func = load_verify_func(cr_unit_test_path)
        data_dict = json.loads(cr_input_path.read_text())
        unit_test_result = verify_func(data_dict, model_output)
        unit_test_pass = is_unit_test_pass(unit_test_result)
    except Exception as e:
        unit_test_error = str(e)
        unit_test_result = {"err": unit_test_error, "err_trace": traceback.format_exc()}
        unit_test_pass = False

    paths.unit_test_log_path.write_text(
        json.dumps(
            {
                "unit_test_pass": unit_test_pass,
                "unit_test_error": unit_test_error,
                "unit_test_result": unit_test_result,
            },
            indent=2,
        )
    )

    status = "pass" if unit_test_pass else "fail"
    result = {
        "problem": problem,
        "cr": cr,
        "status": status,
        "stage": "unit_test",
        "exec_ok": True,
        "unit_test_pass": unit_test_pass,
        "unit_test_result": unit_test_result,
        "expected_output_keys": expected_output_keys,
        "case_dir": str(paths.case_dir),
        "generated_model_path": str(paths.generated_model_path),
        "prompt_path": str(paths.prompt_path),
        "llm_response_path": str(paths.llm_response_path),
        "execution_log_path": str(paths.exec_log_path),
        "unit_test_log_path": str(paths.unit_test_log_path),
    }
    paths.result_path.write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Single-shot baseline runner (OpenAI gpt-5.1-codex-max).")
    parser.add_argument(
        "--problems-root",
        default=str((MODREF_DIR / "problems").resolve()),
        help="Root directory containing problem folders (default: src/mod-ref-benchmark/problems).",
    )
    parser.add_argument(
        "--output-root",
        default=str((THIS_DIR / "results").resolve()),
        help="Output root for baseline results (default: src/mod-ref-benchmark/baseline/results).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        help="Optional OpenAI reasoning effort.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens for OpenAI Responses API.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for executing each generated model (default: 60).",
    )
    parser.add_argument(
        "--only-problem",
        help="Optional: run only a specific problem folder name (e.g., problem1).",
    )
    parser.add_argument(
        "--only-cr",
        help="Optional: run only a specific CR folder name (e.g., CR1).",
    )

    args = parser.parse_args()

    problems_root = Path(args.problems_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    cfg = LLMConfig(
        provider="openai",
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )
    llm = LLMClient(cfg)

    all_results: list[dict[str, Any]] = []

    for problem_dir in sorted(problems_root.iterdir()):
        if not problem_dir.is_dir() or not problem_dir.name.startswith("problem"):
            continue
        if args.only_problem and problem_dir.name != args.only_problem:
            continue

        for cr_dir in sorted(problem_dir.iterdir()):
            if not cr_dir.is_dir() or not cr_dir.name.startswith("CR"):
                continue
            if args.only_cr and cr_dir.name != args.only_cr:
                continue

            print(f"[baseline] Running {problem_dir.name}/{cr_dir.name} with {cfg.model} ...")
            try:
                res = run_single_case(
                    problem_dir=problem_dir,
                    cr_dir=cr_dir,
                    llm=llm,
                    output_root=output_root,
                    timeout=int(args.timeout) if args.timeout else None,
                )
            except Exception as e:
                res = {
                    "problem": problem_dir.name,
                    "cr": cr_dir.name,
                    "status": "fail",
                    "stage": "runner",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            all_results.append(res)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    summary_path = output_root / f"baseline_summary_{timestamp}.json"
    summary = {
        "timestamp": timestamp,
        "llm_config": cfg.to_dict(),
        "counts": {
            "total": len(all_results),
            "pass": sum(1 for r in all_results if r.get("status") == "pass"),
            "fail": sum(1 for r in all_results if r.get("status") == "fail"),
            "skipped": sum(1 for r in all_results if r.get("status") == "skipped"),
        },
        "results": all_results,
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"[baseline] Done. Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
