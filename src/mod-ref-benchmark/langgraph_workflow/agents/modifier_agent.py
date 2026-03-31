import argparse
import json
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent.parent
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from llm_client import LLMClient, LLMConfig, DEFAULT_OPENAI_MODEL, DEFAULT_OPENAI_REASONING_EFFORT
from llm_prompts import build_modifier_prompt, number_code_lines


DEFAULT_MODEL = "gpt-oss:20b"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())



def run_modifier_agent(
    problem_path: str,
    cr_name: str,
    planner_json: str | None = None,
    planner_plan: dict | None = None,
    clarification_transcript: list[dict] | None = None,
    clarified_cr_summary: str | None = None,
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
    numbered_model = number_code_lines(base_model_code)

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
        clarification_transcript=clarification_transcript,
        clarified_cr_summary=clarified_cr_summary,
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
        model_name = DEFAULT_OPENAI_MODEL

    llm_config = {
        "provider": args.provider,
        "model": model_name,
        "reasoning_effort": DEFAULT_OPENAI_REASONING_EFFORT if args.provider == "openai" else None,
    }

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
