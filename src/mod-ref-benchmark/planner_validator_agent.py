import argparse
import datetime
import json
from pathlib import Path

from llm_client import LLMClient, LLMConfig


DEFAULT_MODEL = "gpt-oss:20b"


def _number_code_lines(code: str) -> str:
    """Return code with 1-based line numbers for LLM referencing."""
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def build_planner_validator_schema() -> dict:
    line_range_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "start": {"type": "integer"},
            "end": {"type": "integer"},
        },
        "required": ["start", "end"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["pass", "needs_changes"]},
            "summary": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "missing_change",
                                "incorrect_target",
                                "unnecessary_change",
                                "preservation_risk",
                                "line_reference",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "target_lines": {"anyOf": [line_range_schema, {"type": "null"}]},
                        "suggestion": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                    },
                    "required": [
                        "title",
                        "description",
                        "category",
                        "severity",
                        "target_lines",
                        "suggestion",
                        "confidence",
                    ],
                },
            },
            "notes_for_planner": {"type": "string"},
        },
        "required": ["status", "summary", "issues", "notes_for_planner"],
    }


def build_planner_validator_prompt(
    base_nl_description: str,
    cr_desc: dict,
    parser_mapping: dict,
    planner_output: dict,
    numbered_model: str,
    schema: dict,
) -> str:
    return f"""
You are the Planner Validator agent. Review the planner output before any code is generated.

Your job:
- Check whether the plan fully covers the Change Request.
- Check whether the line targets are plausible given the parser mapping and reference model.
- Check whether the plan protects unaffected sections instead of proposing unnecessary changes.
- Do NOT write code and do NOT run code.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Guidelines:
- Return status "pass" only if the plan is specific, aligned with the CR, and safe for the modifier to execute.
- Return status "needs_changes" if the plan is missing a required edit, targets the wrong code, proposes unnecessary edits, or leaves preservation risks.
- Keep feedback concise and directly actionable for the Planner agent.
- Use 1-based line numbers when pointing to issues in the reference model.
- If an issue cannot be localized to exact lines, set target_lines to null.

Base problem description:
{base_nl_description}

Change Request JSON:
{json.dumps(cr_desc, indent=2)}

Parser mapping:
{json.dumps(parser_mapping, indent=2)}

Planner output to review:
{json.dumps(planner_output, indent=2)}

Reference model with line numbers:
{numbered_model}
"""


def run_planner_validator_agent(
    problem_path: str,
    cr_name: str,
    planner_output: dict,
    parser_mapping: dict,
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
    numbered_model = _number_code_lines(base_model_code)
    cr_desc = json.loads(cr_desc_path.read_text())

    schema = build_planner_validator_schema()
    prompt = build_planner_validator_prompt(
        base_nl_description=base_nl_description,
        cr_desc=cr_desc,
        parser_mapping=parser_mapping,
        planner_output=planner_output,
        numbered_model=numbered_model,
        schema=schema,
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

    planner_payload = json.loads(Path(args.planner_json).read_text())
    parser_payload = json.loads(Path(args.parser_json).read_text())
    planner_output = planner_payload.get("planner_output", planner_payload)
    parser_mapping = parser_payload.get("parser_output", parser_payload)

    model_name = args.model_name
    if args.provider == "openai" and model_name == DEFAULT_MODEL:
        model_name = "gpt-4o-mini"

    llm_config = {"provider": args.provider, "model": model_name}
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
