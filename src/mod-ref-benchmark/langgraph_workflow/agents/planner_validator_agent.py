import argparse
import datetime
import json
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent.parent
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from llm_client import (
    LLMClient,
    LLMConfig,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_REASONING_EFFORT,
    DEFAULT_OPENROUTER_MODEL,
)
from llm_prompts import build_planner_validator_prompt, number_code_lines
from llm_schemas import build_planner_validator_schema


DEFAULT_MODEL = "gpt-oss:20b"


def run_planner_validator_agent(
    problem_path: str,
    cr_name: str,
    planner_output: dict,
    parser_mapping: dict,
    clarification_transcript: list[dict] | None = None,
    clarified_cr_summary: str | None = None,
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

    for path in [desc_path, model_path, cr_desc_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required file at {path}")

    base_nl_description = desc_path.read_text()
    base_model_code = model_path.read_text()
    numbered_model = number_code_lines(base_model_code)
    cr_desc = json.loads(cr_desc_path.read_text())

    schema = build_planner_validator_schema()
    prompt = build_planner_validator_prompt(
        base_nl_description=base_nl_description,
        cr_desc=cr_desc,
        parser_mapping=parser_mapping,
        planner_output=planner_output,
        numbered_model=numbered_model,
        schema=schema,
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
    validator_output = llm.generate_json(
        prompt=prompt,
        schema=schema,
        schema_name="planner_validator_output",
        system="You are a precise reviewer of CPMPy edit plans.",
    )

    output_file: Path | None = None
    if output_path is not False:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if output_path is None:
            output_file = cr_dir / f"{problem_dir.name}_{cr_name}_planner_validator_{timestamp}.json"
        else:
            output_file = Path(output_path)
            if not output_file.is_absolute():
                output_file = cr_dir / output_file

        payload = {
            "problem": problem_dir.name,
            "cr": cr_name,
            "timestamp": timestamp,
            "planner_output": planner_output,
            "planner_validator_output": validator_output,
        }
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, indent=2))

    return validator_output, output_file


def main():
    parser = argparse.ArgumentParser(description="Planner validator agent: review planner output before modification.")
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument("--planner-json", required=True, help="Path to planner output JSON.")
    parser.add_argument("--parser-json", required=True, help="Path to parser output JSON.")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "openrouter"],
        default="ollama",
        help="LLM provider to use (default: ollama).",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL,
        help="Model name to use (default: gpt-oss:20b).",
    )
    args = parser.parse_args()

    planner_payload = json.loads(Path(args.planner_json).read_text())
    parser_payload = json.loads(Path(args.parser_json).read_text())
    planner_output = planner_payload.get("planner_output", planner_payload)
    parser_mapping = parser_payload.get("parser_output", parser_payload)

    model_name = args.model_name
    if args.provider == "openai" and model_name == DEFAULT_MODEL:
        model_name = DEFAULT_OPENAI_MODEL
    elif args.provider == "openrouter" and model_name == DEFAULT_MODEL:
        model_name = DEFAULT_OPENROUTER_MODEL

    llm_config = {
        "provider": args.provider,
        "model": model_name,
        "reasoning_effort": DEFAULT_OPENAI_REASONING_EFFORT if args.provider == "openai" else None,
    }
    validator_output, output_file = run_planner_validator_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        planner_output=planner_output,
        parser_mapping=parser_mapping,
        llm_config=llm_config,
        model_name=model_name,
    )
    print(f"Planner validator completed. Saved report to {output_file}")
    print(f"Status: {validator_output.get('status')}")


if __name__ == "__main__":
    main()
