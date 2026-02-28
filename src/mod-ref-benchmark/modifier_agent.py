import argparse
import json
import re
from pathlib import Path

from llm_client import LLMClient, LLMConfig


DEFAULT_MODEL = "gpt-oss:20b"


def _number_code_lines(code: str) -> str:
    """Return code with 1-based line numbers for LLM referencing."""
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())

def extract_output_keys(ref_sol_format: dict) -> list[str]:
    """
    ref_sol_format uses placeholder keys like 'var1'. The real output keys are
    embedded as backtick-quoted identifiers in each entry's 'descr' field.
    """
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


def build_modifier_prompt(
    base_nl_description: str,
    cr_desc: dict,
    planner_plan: dict,
    base_model_code: str,
    numbered_model: str,
    previous_code: str | None,
    error_message: str | None,
) -> str:
    cr_text = cr_desc.get("content", "")
    value_info = cr_desc.get("value_info", [])
    ref_sol_format = cr_desc.get("ref_sol_format", {})
    expected_output_keys = extract_output_keys(ref_sol_format)

    planner_text = json.dumps(planner_plan, indent=2)
    ref_sol_text = json.dumps(ref_sol_format, indent=2)
    value_info_text = json.dumps(value_info, indent=2)

    prompt = f"""
You are the Modifier agent. Apply the change request to the CPMPy reference model with minimal edits, following the planner instructions. 
Preserve existing constraints unless a planner step says to change them. Do not remove functionality unrelated to the CR. Only ouput valid Python CPMPy code NOT SURROUNDED BY MARKDOWN OR BACKTICKS.

Base problem description (NL):
{base_nl_description}

Change Request (content):
{cr_text}

Parameter description (value_info):
{value_info_text}

Expected output format (ref_sol_format):
{ref_sol_text}

CRITICAL INSTRUCTION ABOUT OUTPUT KEYS:
- Keys like "var1", "var2", ... in ref_sol_format are ONLY placeholders.
- You MUST output the REAL keys, extracted from the backtick-quoted identifier in each ref_sol_format[*]["descr"] field.
- For this CR, the expected top-level JSON keys are: {expected_output_keys}
- Example: if descr contains "`sequence`:", the output JSON must contain the key "sequence" (NOT "var1").

Planner edit plan (authoritative):
{planner_text}

Reference CPMPy model (without line numbers):
{base_model_code}

Reference CPMPy model with line numbers:
{numbered_model}

Requirements:
- Implement the planner steps (add/modify constraints/objective) precisely; prefer editing the pointed line ranges or inserting after suggested lines.
- Keep all other constraints and structure intact.
- Load all numeric parameters from 'input_data.json' at runtime using the names from value_info; never hard-code instance data.
- Do NOT add hardcoded solve limits (e.g., model.solve(time_limit=...)) unless the CR explicitly requests runtime limiting; otherwise use plain model.solve().
- Respect ref_sol_format variable names when printing the solution dictionary; avoid placeholder keys like 'var1'.
- Output valid Python CPMPy code only; no markdown, no extra text. The final line must print the JSON.
- If the planner suggests a new objective, set it; otherwise keep existing objective semantics unchanged.


Formatting rules:
  - Output ONLY valid Python CPMPy code.
  - Do NOT include markdown, python backticks, comments, or explanations.
  - The final line must be a print(json.dumps(...)).
    IMPORTANT:
        - DO NOT include any text before the Python code.
        - DO NOT include ```python ```, just the code.
        - DO NOT prefix with explanations, comments, markdown, or warnings.
        - If you want to include comments, include only Python # comments.
"""

    if previous_code or error_message:
        prompt += f"""

Previous attempt code:
{previous_code or "(none)"}

Error to fix (if any):
{error_message or "(none)"}

Revise the code to fix the issue while keeping all requirements above.
"""

    return prompt


def run_modifier_agent(
    problem_path: str,
    cr_name: str,
    planner_json: str | None = None,
    planner_plan: dict | None = None,
    base_desc_filename: str = "problem_desc.txt",
    base_model_filename: str = "reference_model.py",
    output_filename: str = "generated_model.py",
    llm_config: dict | LLMConfig | None = None,
    model_name: str = DEFAULT_MODEL,
    previous_code: str | None = None,
    error_message: str | None = None,
) -> tuple[str, Path, Path | None]:
    problem_dir = Path(problem_path)
    cr_dir = problem_dir / cr_name
    base_dir = problem_dir / "base"

    desc_path = base_dir / base_desc_filename
    model_path = base_dir / base_model_filename
    cr_desc_path = cr_dir / "desc.json"
    planner_json_path = Path(planner_json) if planner_json else None

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing base description at {desc_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing base model at {model_path}")
    if not cr_desc_path.exists():
        raise FileNotFoundError(f"Missing CR desc at {cr_desc_path}")
    if planner_json_path is None and planner_plan is None:
        raise FileNotFoundError("Planner plan not provided (need planner_json path or planner_plan dict).")
    if planner_json_path is not None and not planner_json_path.exists():
        raise FileNotFoundError(f"Missing planner JSON at {planner_json_path}")

    base_nl_description = desc_path.read_text()
    base_model_code = model_path.read_text()
    numbered_model = _number_code_lines(base_model_code)

    cr_desc = load_json(cr_desc_path)
    planner_data = planner_plan or load_json(planner_json_path)
    planner_plan = planner_data.get("planner_output", planner_data)

    prompt = build_modifier_prompt(
        base_nl_description=base_nl_description,
        cr_desc=cr_desc,
        planner_plan=planner_plan,
        base_model_code=base_model_code,
        numbered_model=numbered_model,
        previous_code=previous_code,
        error_message=error_message,
    )

    if llm_config is None:
        cfg = LLMConfig(provider="ollama", model=model_name)
    elif isinstance(llm_config, dict):
        cfg = LLMConfig.from_dict(llm_config)
    else:
        cfg = llm_config

    llm = LLMClient(cfg)
    code = llm.generate_text(prompt=prompt)

    output_path = cr_dir / output_filename
    output_path.write_text(code)

    log_path: Path | None = None
    return code, output_path, log_path


def main():
    parser = argparse.ArgumentParser(
        description="Modifier agent: apply planner steps to update the CPMPy model for a CR."
    )
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument("--planner-json", required=True, help="Path to the planner agent JSON output.")
    parser.add_argument(
        "--base-desc",
        default="problem_desc.txt",
        help="Filename of the base natural language description inside the base folder.",
    )
    parser.add_argument(
        "--base-model",
        default="reference_model.py",
        help="Filename of the base CPMPy model inside the base folder.",
    )
    parser.add_argument(
        "--output-filename",
        default="generated_model.py",
        help="Filename for the generated CPMPy model inside the CR folder.",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai"],
        default="ollama",
        help="LLM provider to use (default: ollama).",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL,
        help="Model name to use (default: gpt-oss:20b).",
    )

    args = parser.parse_args()
    model_name = args.model_name
    if args.provider == "openai" and model_name == DEFAULT_MODEL:
        model_name = "gpt-5.1-codex-max"

    llm_config = {"provider": args.provider, "model": model_name}

    code, output_path, _ = run_modifier_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        planner_json=args.planner_json,
        base_desc_filename=args.base_desc,
        base_model_filename=args.base_model,
        output_filename=args.output_filename,
        llm_config=llm_config,
        model_name=model_name,
    )

    print(f"Modifier agent completed. Saved model to {output_path}")
    print(f"Generated code length: {len(code)} characters.")


if __name__ == "__main__":
    main()
