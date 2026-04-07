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
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent  # src/mod-ref-benchmark
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from baseline_cost_estimation import estimate_baseline_run_cost, load_case_prompt_info
from llm_client import LLMClient, LLMConfig
from llm_schemas import build_code_schema
from model_presets import select_model_presets


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


def run_python_script(*, script_path: Path, cwd: Path, timeout: int | None = None) -> tuple[dict[str, Any] | None, str, str, int]:
    """Run a Python script and return parsed JSON, stdout, stderr, and return code."""
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


def iter_cases(problems_root: Path, only_problem: str | None, only_cr: str | None):
    for problem_dir in sorted(problems_root.iterdir()):
        if not problem_dir.is_dir() or not problem_dir.name.startswith("problem"):
            continue
        if only_problem and problem_dir.name != only_problem:
            continue

        for cr_dir in sorted(problem_dir.iterdir()):
            if not cr_dir.is_dir() or not cr_dir.name.startswith("CR"):
                continue
            if only_cr and cr_dir.name != only_cr:
                continue
            yield problem_dir, cr_dir


def build_llm_config(*, provider: str, model: str | None, reasoning_effort: str | None, max_output_tokens: int | None) -> LLMConfig:
    return LLMConfig.from_dict(
        {
            "provider": provider,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "max_output_tokens": max_output_tokens,
        }
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
        result = {
            "problem": problem,
            "cr": cr,
            "status": "skipped",
            "stage": "discovery",
            "error": f"Missing required files: {[str(p) for p in missing]}",
            "case_dir": str(paths.case_dir),
            "result_path": str(paths.result_path),
        }
        paths.result_path.write_text(json.dumps(result, indent=2))
        return result

    prompt_info = load_case_prompt_info(problem_dir, cr_dir)
    expected_output_keys = prompt_info.expected_output_keys
    prompt = prompt_info.prompt
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
    except Exception as exc:
        generation_error = str(exc)

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
            "result_path": str(paths.result_path),
        }
        paths.result_path.write_text(json.dumps(result, indent=2))
        return result

    assert code is not None
    paths.generated_model_path.write_text(code)
    shutil.copy2(cr_input_path, paths.case_dir / "input_data.json")

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
            "result_path": str(paths.result_path),
        }
        paths.result_path.write_text(json.dumps(result, indent=2))
        return result

    unit_test_pass = False
    unit_test_result: Any = None
    unit_test_error: str | None = None
    try:
        verify_func = load_verify_func(cr_unit_test_path)
        data_dict = json.loads(cr_input_path.read_text())
        unit_test_result = verify_func(data_dict, model_output)
        unit_test_pass = is_unit_test_pass(unit_test_result)
    except Exception as exc:
        unit_test_error = str(exc)
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
        "result_path": str(paths.result_path),
    }
    paths.result_path.write_text(json.dumps(result, indent=2))
    return result


def normalize_model_key(provider: str, model: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in f"{provider}_{model}".lower()).strip("_")


def print_cost_estimate_summary(*, estimate: dict[str, Any], estimate_path: Path) -> None:
    totals = estimate.get("totals", {})
    print(
        "[baseline] Cost estimate: "
        f"{totals.get('models', 0)} model(s), "
        f"{totals.get('selected_cases', 0)} case(s), "
        f"{totals.get('invocations', 0)} invocation(s).",
        flush=True,
    )
    for model_data in estimate.get("models", []):
        model_totals = model_data.get("totals", {})
        model_key = model_data.get("model_key")
        if model_totals.get("cost_complete"):
            print(
                "[baseline]   "
                f"{model_key}: "
                f"lower=${model_totals.get('lower_cost'):.6f} | "
                f"expected=${model_totals.get('expected_cost'):.6f} | "
                f"upper=${model_totals.get('upper_cost'):.6f}",
                flush=True,
            )
        else:
            pricing_note = (model_data.get("pricing") or {}).get("note") or "pricing unavailable"
            print(
                "[baseline]   "
                f"{model_key}: pricing unavailable, "
                f"input_tokens={model_totals.get('input_tokens', 0)}, "
                f"expected_output_tokens={model_totals.get('expected_output_tokens', 0)} "
                f"({pricing_note})",
                flush=True,
            )

    if totals.get("cost_complete"):
        print(
            "[baseline] Overall estimate: "
            f"lower=${totals.get('lower_cost'):.6f} | "
            f"expected=${totals.get('expected_cost'):.6f} | "
            f"upper=${totals.get('upper_cost'):.6f}",
            flush=True,
        )
    else:
        print(
            "[baseline] Overall estimate: partial pricing only; "
            f"unpriced_models={totals.get('unpriced_models', [])}",
            flush=True,
        )
    print(f"[baseline] Cost estimate saved to {estimate_path}", flush=True)


def summarize_case(*, model_spec: dict[str, Any], result: dict[str, Any] | None, error: Exception | None = None) -> dict[str, Any]:
    summary = {
        "model_key": model_spec["key"],
        "model_label": model_spec["label"],
        "provider": model_spec["provider"],
        "model": model_spec["model"],
        "reasoning_effort": model_spec.get("reasoning_effort"),
        "docs_url": model_spec.get("docs_url"),
    }

    if error is not None:
        summary.update(
            {
                "status": "fail",
                "stage": "runner",
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
        )
        return summary

    payload = result or {}
    summary.update(
        {
            "problem": payload.get("problem"),
            "cr": payload.get("cr"),
            "status": payload.get("status", "fail"),
            "stage": payload.get("stage"),
            "error": payload.get("error"),
            "exec_error": payload.get("exec_error"),
            "unit_test_pass": payload.get("unit_test_pass"),
            "case_dir": payload.get("case_dir"),
            "generated_model_path": payload.get("generated_model_path"),
            "prompt_path": payload.get("prompt_path"),
            "llm_response_path": payload.get("llm_response_path"),
            "execution_log_path": payload.get("execution_log_path"),
            "unit_test_log_path": payload.get("unit_test_log_path"),
            "result_path": payload.get("result_path"),
        }
    )
    return summary


def run_preset_cases(
    *,
    model_spec: dict[str, Any],
    problems_root: Path,
    output_root: Path,
    only_problem: str | None,
    only_cr: str | None,
    max_output_tokens: int | None,
    timeout: int | None,
) -> list[dict[str, Any]]:
    cfg = build_llm_config(
        provider=model_spec["provider"],
        model=model_spec["model"],
        reasoning_effort=model_spec.get("reasoning_effort"),
        max_output_tokens=max_output_tokens,
    )
    llm = LLMClient(cfg)
    model_output_root = output_root / model_spec["key"]
    model_output_root.mkdir(parents=True, exist_ok=True)

    model_results: list[dict[str, Any]] = []
    for problem_dir, cr_dir in iter_cases(problems_root, only_problem, only_cr):
        print(f"[baseline] Running {model_spec['key']} on {problem_dir.name}/{cr_dir.name} ...", flush=True)
        try:
            res = run_single_case(
                problem_dir=problem_dir,
                cr_dir=cr_dir,
                llm=llm,
                output_root=model_output_root,
                timeout=timeout,
            )
            summary = summarize_case(model_spec=model_spec, result=res)
        except Exception as exc:
            summary = summarize_case(
                model_spec=model_spec,
                result={"problem": problem_dir.name, "cr": cr_dir.name},
                error=exc,
            )
        model_results.append(summary)
    return model_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline runner for single-shot code generation across one or more model presets.")
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
        "--only-model",
        action="append",
        help="Optional preset key to run. Repeat to run more than one model.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "openrouter", "ollama"],
        help="Ad hoc mode only: provider for a single manual model run.",
    )
    parser.add_argument(
        "--model",
        help="Ad hoc mode only: model name for a single manual model run.",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high"],
        help="Ad hoc mode only: reasoning effort to pass to the LLM client.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens passed through to the LLM client.",
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
    parser.add_argument(
        "--estimate-cost-only",
        action="store_true",
        help="Compute and save a pre-run cost estimate, then exit before any model calls.",
    )
    args = parser.parse_args()

    ad_hoc_mode = any(value is not None for value in (args.provider, args.model, args.reasoning_effort))
    if ad_hoc_mode and args.only_model:
        raise ValueError("Use either preset selection via --only-model or ad hoc --provider/--model flags, not both.")

    problems_root = Path(args.problems_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timeout = int(args.timeout) if args.timeout else None
    run_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if ad_hoc_mode:
        cfg = build_llm_config(
            provider=args.provider or "openai",
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            max_output_tokens=args.max_output_tokens,
        )
        selected_models = [
            {
                "key": normalize_model_key(cfg.provider, cfg.model),
                "label": f"Ad hoc {cfg.provider}:{cfg.model}",
                "provider": cfg.provider,
                "model": cfg.model,
                "reasoning_effort": cfg.reasoning_effort,
                "docs_url": None,
            }
        ]
    else:
        selected_models = select_model_presets(args.only_model)

    cases = list(iter_cases(problems_root, args.only_problem, args.only_cr))
    cost_estimate = estimate_baseline_run_cost(
        cases=cases,
        model_specs=selected_models,
        max_output_tokens=args.max_output_tokens,
    )
    cost_estimate.update(
        {
            "problems_root": str(problems_root),
            "output_root": str(output_root),
            "selected_models": selected_models,
            "filters": {
                "only_model": args.only_model or [],
                "only_problem": args.only_problem,
                "only_cr": args.only_cr,
            },
        }
    )
    estimate_path = output_root / f"baseline_cost_estimate_{run_timestamp}.json"
    estimate_path.write_text(json.dumps(cost_estimate, indent=2))
    print_cost_estimate_summary(estimate=cost_estimate, estimate_path=estimate_path)

    if args.estimate_cost_only:
        print("[baseline] Estimate-only mode enabled; exiting before any model calls.", flush=True)
        return

    all_results: list[dict[str, Any]] = []
    for model_spec in selected_models:
        model_results = run_preset_cases(
            model_spec=model_spec,
            problems_root=problems_root,
            output_root=output_root,
            only_problem=args.only_problem,
            only_cr=args.only_cr,
            max_output_tokens=args.max_output_tokens,
            timeout=timeout,
        )
        all_results.extend(model_results)

        model_summary = {
            "timestamp": run_timestamp,
            "model_key": model_spec["key"],
            "model_label": model_spec["label"],
            "provider": model_spec["provider"],
            "model": model_spec["model"],
            "reasoning_effort": model_spec.get("reasoning_effort"),
            "docs_url": model_spec.get("docs_url"),
            "cost_estimate": next(
                (model_data.get("totals") for model_data in cost_estimate.get("models", []) if model_data.get("model_key") == model_spec["key"]),
                None,
            ),
            "counts": {
                "total": len(model_results),
                "pass": sum(1 for item in model_results if item.get("status") == "pass"),
                "fail": sum(1 for item in model_results if item.get("status") == "fail"),
                "skipped": sum(1 for item in model_results if item.get("status") == "skipped"),
            },
            "results": model_results,
        }
        model_summary_path = output_root / model_spec["key"] / f"model_summary_{run_timestamp}.json"
        model_summary_path.write_text(json.dumps(model_summary, indent=2))

    overall_summary = {
        "timestamp": run_timestamp,
        "problems_root": str(problems_root),
        "output_root": str(output_root),
        "max_output_tokens": args.max_output_tokens,
        "timeout": timeout,
        "cost_estimate_path": str(estimate_path),
        "cost_estimate": {
            "totals": cost_estimate.get("totals", {}),
            "models": [
                {
                    "model_key": model_data.get("model_key"),
                    "model_label": model_data.get("model_label"),
                    "totals": model_data.get("totals"),
                    "pricing": model_data.get("pricing"),
                }
                for model_data in cost_estimate.get("models", [])
            ],
        },
        "selected_models": selected_models,
        "counts": {
            "total": len(all_results),
            "pass": sum(1 for item in all_results if item.get("status") == "pass"),
            "fail": sum(1 for item in all_results if item.get("status") == "fail"),
            "skipped": sum(1 for item in all_results if item.get("status") == "skipped"),
        },
        "results": all_results,
    }
    summary_path = output_root / f"baseline_experiment_summary_{run_timestamp}.json"
    summary_path.write_text(json.dumps(overall_summary, indent=2))
    print(f"[baseline] Done. Summary saved to {summary_path}", flush=True)


if __name__ == "__main__":
    main()
