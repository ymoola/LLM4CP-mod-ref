import argparse
import datetime
import json
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent.parent
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from llm_client import LLMClient, LLMConfig, DEFAULT_OPENAI_MODEL, DEFAULT_OPENAI_REASONING_EFFORT
from llm_prompts import build_planner_prompt, number_code_lines
from llm_schemas import build_planner_schema


DEFAULT_MODEL = "gpt-oss:20b"


def load_parser_output(parser_json_path: Path) -> dict:
    """Load the parser agent output, unwrapping if stored under 'parser_output'."""
    data = json.loads(parser_json_path.read_text())
    return data.get("parser_output", data)




def run_planner_agent(
    problem_path: str,
    cr_name: str,
    parser_json: str | None = None,
    parser_mapping: dict | None = None,
    previous_plan: dict | None = None,
    feedback: str | None = None,
    base_desc_filename: str = "problem_desc.txt",
    base_model_filename: str = "reference_model.py",
    output_path: str | None = None,
    llm_config: dict | LLMConfig | None = None,
    model_name: str = DEFAULT_MODEL,
) -> tuple[dict, Path | None]:
    problem_dir = Path(problem_path)
    cr_dir = problem_dir / cr_name
    base_dir = problem_dir / "base"

    desc_path = base_dir / base_desc_filename
    model_path = base_dir / base_model_filename
    cr_desc_path = cr_dir / "desc.json"
    parser_json_path = Path(parser_json) if parser_json else None

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing base description at {desc_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing base model at {model_path}")
    if not cr_desc_path.exists():
        raise FileNotFoundError(f"Missing CR desc at {cr_desc_path}")
    if parser_json_path is None and parser_mapping is None:
        raise FileNotFoundError("Parser mapping not provided (need parser_json path or parser_mapping dict).")
    if parser_json_path is not None and not parser_json_path.exists():
        raise FileNotFoundError(f"Missing parser JSON at {parser_json_path}")

    base_nl_description = desc_path.read_text()
    base_model_code = model_path.read_text()
    numbered_model = number_code_lines(base_model_code)

    cr_desc = json.loads(cr_desc_path.read_text())
    parser_mapping = parser_mapping or load_parser_output(parser_json_path)

    schema = build_planner_schema()
    prompt = build_planner_prompt(
        base_nl_description,
        cr_desc,
        numbered_model,
        parser_mapping,
        schema,
        previous_plan=previous_plan,
        feedback=feedback,
    )

    if llm_config is None:
        cfg = LLMConfig(provider="ollama", model=model_name)
    elif isinstance(llm_config, dict):
        cfg = LLMConfig.from_dict(llm_config)
    else:
        cfg = llm_config

    llm = LLMClient(cfg)
    planner_output = llm.generate_json(
        prompt=prompt,
        schema=schema,
        schema_name="planner_output",
        system="You draft minimal, actionable edit plans for CPMPy models given a CR.",
    )

    output_file: Path | None = None
    if output_path is not False:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if output_path is None:
            output_file = cr_dir / f"{problem_dir.name}_{cr_name}_planner.json"
        else:
            output_file = Path(output_path)
            if not output_file.is_absolute():
                output_file = cr_dir / output_file

        payload = {
            "problem": problem_dir.name,
            "cr": cr_name,
            "base_desc": str(desc_path),
            "base_model": str(model_path),
            "cr_desc": str(cr_desc_path),
            "parser_json": str(parser_json_path),
            "timestamp": timestamp,
            "llm_model": model_name,
            "planner_output": planner_output,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, indent=2))

    return planner_output, output_file


def main():
    parser = argparse.ArgumentParser(
        description="Planner agent: produce an edit plan for a CR using parser mappings and the reference model."
    )
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument("--parser-json", required=True, help="Path to the parser agent JSON output.")
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
    parser.add_argument(
        "--output",
        help="Optional output JSON path. Defaults to <problem>/<cr>/<problem>_<cr>_planner_<timestamp>.json.",
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
    planner_output, output_file = run_planner_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        parser_json=args.parser_json,
        base_desc_filename=args.base_desc,
        base_model_filename=args.base_model,
        output_path=args.output,
        llm_config=llm_config,
        model_name=model_name,
    )

    print(f"Planner agent completed. Saved plan to {output_file}")
    print(f"Planned {len(planner_output.get('plan', []))} changes.")


if __name__ == "__main__":
    main()
