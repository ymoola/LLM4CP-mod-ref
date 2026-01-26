import argparse
import datetime
import json
from pathlib import Path

import ollama


DEFAULT_MODEL = "gpt-oss:20b"


def _number_code_lines(code: str) -> str:
    """Return code with 1-based line numbers for LLM referencing."""
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def load_parser_output(parser_json_path: Path) -> dict:
    """Load the parser agent output, unwrapping if stored under 'parser_output'."""
    data = json.loads(parser_json_path.read_text())
    return data.get("parser_output", data)


def build_planner_schema() -> dict:
    """Schema for structured planner output."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "change_type": {
                            "type": "string",
                            "enum": [
                                "add_constraint",
                                "modify_constraint",
                                "remove_constraint",
                                "add_objective",
                                "modify_objective",
                                "data_handling",
                                "other",
                            ],
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "related_nl": {"type": "string"},
                        "target_lines": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                            },
                            "required": ["start", "end"],
                        },
                        "insert_after_line": {"type": "integer"},
                        "code_excerpt": {"type": "string"},
                        "strategy": {"type": "string"},
                        "confidence": {"type": "number"},
                        "risks": {"type": "string"},
                    },
                    "required": ["change_type", "title", "description", "related_nl", "strategy"],
                },
            },
            "preserve_sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "model_lines": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                            },
                            "required": ["start", "end"],
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["model_lines", "reason"],
                },
            },
            "notes_for_modifier": {"type": "string"},
        },
        "required": ["plan"],
    }


def build_planner_prompt(
    base_nl_description: str,
    cr_desc: dict,
    numbered_model: str,
    parser_mapping: dict,
    schema: dict,
) -> str:
    schema_text = json.dumps(schema, indent=2)
    cr_pretty = json.dumps(cr_desc, indent=2)
    mapping_text = json.dumps(parser_mapping, indent=2)
    return f"""
You are the Planner agent. Given a change request (CR) and the existing CPMPy model, produce a precise edit plan indicating what needs to change (add/modify constraints or objectives) and where.

Output must follow this JSON schema (also enforced via structured output):
{schema_text}

Guidelines:
- Use 1-based line numbers from the numbered model listing.
- Prefer pointing to existing constraints to modify; if adding, suggest nearby line to insert (insert_after_line).
- Keep strategy concise but actionable for the Modifier agent (no full code, just how to implement).
- Do NOT propose changes unrelated to the CR; highlight sections to preserve so the modifier avoids regressions.
- If confidence is low, note risks.

Change Request (CR) JSON:
{cr_pretty}

Base problem description (NL):
{base_nl_description}

Parser mapping (NL to code):
{mapping_text}

Numbered CPMPy reference model:
{numbered_model}
"""


def run_planner_agent(
    problem_path: str,
    cr_name: str,
    parser_json: str,
    base_desc_filename: str = "problem_desc.txt",
    base_model_filename: str = "reference_model.py",
    output_path: str | None = None,
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> tuple[dict, Path]:
    problem_dir = Path(problem_path)
    cr_dir = problem_dir / cr_name
    base_dir = problem_dir / "base"

    desc_path = base_dir / base_desc_filename
    model_path = base_dir / base_model_filename
    cr_desc_path = cr_dir / "desc.json"
    parser_json_path = Path(parser_json)

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing base description at {desc_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing base model at {model_path}")
    if not cr_desc_path.exists():
        raise FileNotFoundError(f"Missing CR desc at {cr_desc_path}")
    if not parser_json_path.exists():
        raise FileNotFoundError(f"Missing parser JSON at {parser_json_path}")

    base_nl_description = desc_path.read_text()
    base_model_code = model_path.read_text()
    numbered_model = _number_code_lines(base_model_code)

    cr_desc = json.loads(cr_desc_path.read_text())
    parser_mapping = load_parser_output(parser_json_path)

    schema = build_planner_schema()
    prompt = build_planner_prompt(base_nl_description, cr_desc, numbered_model, parser_mapping, schema)

    response = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": "You draft minimal, actionable edit plans for CPMPy models given a CR."},
            {"role": "user", "content": prompt},
        ],
        format=schema,
        options={"temperature": temperature},
    )

    raw_content = response["message"]["content"]
    try:
        planner_output = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}\nRaw content: {raw_content}") from exc

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
        "--model-name",
        default=DEFAULT_MODEL,
        help="Ollama model name to use (default: gpt-oss:20b).",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path. Defaults to <problem>/<cr>/<problem>_<cr>_planner_<timestamp>.json.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature passed to the LLM for determinism (default: 0.0).",
    )

    args = parser.parse_args()
    planner_output, output_file = run_planner_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        parser_json=args.parser_json,
        base_desc_filename=args.base_desc,
        base_model_filename=args.base_model,
        output_path=args.output,
        model_name=args.model_name,
        temperature=args.temperature,
    )

    print(f"Planner agent completed. Saved plan to {output_file}")
    print(f"Planned {len(planner_output.get('plan', []))} changes.")


if __name__ == "__main__":
    main()
