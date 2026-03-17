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
from llm_prompts import build_validator_prompt, number_code_lines
from llm_schemas import build_validator_schema


DEFAULT_MODEL = "gpt-oss:20b"


def run_validator_agent(
    problem_path: str,
    cr_name: str,
    generated_model_filename: str = "generated_model.py",
    base_desc_filename: str = "problem_desc.txt",
    base_model_filename: str = "reference_model.py",
    cr_desc_filename: str = "desc.json",
    output_path: str | None = None,
    llm_config: dict | LLMConfig | None = None,
    model_name: str = DEFAULT_MODEL,
) -> tuple[dict, Path | None]:
    problem_dir = Path(problem_path)
    cr_dir = problem_dir / cr_name
    base_dir = problem_dir / "base"

    base_desc_path = base_dir / base_desc_filename
    reference_model_path = base_dir / base_model_filename
    generated_model_path = cr_dir / generated_model_filename
    cr_desc_path = cr_dir / cr_desc_filename

    for path in [base_desc_path, reference_model_path, generated_model_path, cr_desc_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required file at {path}")

    base_nl_description = base_desc_path.read_text()
    reference_model_code = reference_model_path.read_text()
    generated_model_code = generated_model_path.read_text()
    cr_desc = json.loads(cr_desc_path.read_text())

    numbered_reference = number_code_lines(reference_model_code)
    numbered_generated = number_code_lines(generated_model_code)

    schema = build_validator_schema()
    prompt = build_validator_prompt(
        base_nl_description=base_nl_description,
        cr_desc=cr_desc,
        reference_model_code=reference_model_code,
        generated_model_code=generated_model_code,
        numbered_reference=numbered_reference,
        numbered_generated=numbered_generated,
        schema=schema,
    )

    try:
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
            schema_name="validator_output",
            system="You are a precise code reviewer for CPMPy change requests.",
        )
    except Exception as exc:
        # Fallback: synthesize a needs_changes response so the workflow can continue
        validator_output = {
            "status": "needs_changes",
            "summary": "Validator LLM returned invalid JSON; see suggestion.",
            "issues": [
                {
                    "title": "Validator JSON parse failure",
                    "description": f"{exc}",
                    "category": "other",
                    "severity": "high",
                    "suggestion": "Retry validation with stricter JSON formatting in the LLM call.",
                    "confidence": 0.1,
                    "generated_lines": {"start": 1, "end": 1},
                    "reference_lines": {"start": 1, "end": 1},
                }
            ],
            "notes_for_modifier": "Validator failed to produce parseable JSON; retry validation.",
        }

    output_file: Path | None = None
    if output_path is not False:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if output_path is None:
            output_file = cr_dir / f"{problem_dir.name}_{cr_name}_validator_{timestamp}.json"
        else:
            output_file = Path(output_path)
            if not output_file.is_absolute():
                output_file = cr_dir / output_file

        payload = {
            "problem": problem_dir.name,
            "cr": cr_name,
            "generated_model": str(generated_model_path),
            "reference_model": str(reference_model_path),
            "base_desc": str(base_desc_path),
            "cr_desc": str(cr_desc_path),
            "timestamp": timestamp,
            "llm_model": model_name,
            "validator_output": validator_output,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, indent=2))

    return validator_output, output_file


def main():
    parser = argparse.ArgumentParser(
        description="Validator agent: LLM check that generated model satisfies the CR without regressions."
    )
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument(
        "--generated-model",
        default="generated_model.py",
        help="Generated model filename inside the CR folder.",
    )
    parser.add_argument(
        "--base-desc",
        default="problem_desc.txt",
        help="Base NL description filename inside the base folder.",
    )
    parser.add_argument(
        "--base-model",
        default="reference_model.py",
        help="Reference model filename inside the base folder.",
    )
    parser.add_argument(
        "--cr-desc",
        default="desc.json",
        help="CR description filename inside the CR folder.",
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
        help="Optional output JSON path. Defaults to <problem>/<cr>/<problem>_<cr>_validator_<timestamp>.json.",
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

    validator_output, output_file = run_validator_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        generated_model_filename=args.generated_model,
        base_desc_filename=args.base_desc,
        base_model_filename=args.base_model,
        cr_desc_filename=args.cr_desc,
        output_path=args.output,
        llm_config=llm_config,
        model_name=model_name,
    )

    print(f"Validator agent completed. Saved report to {output_file}")
    print(f"Status: {validator_output.get('status')}")


if __name__ == "__main__":
    main()
