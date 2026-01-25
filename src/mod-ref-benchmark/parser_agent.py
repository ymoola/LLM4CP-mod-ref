import argparse
import datetime
import json
from pathlib import Path

import ollama


DEFAULT_MODEL = "gpt-oss:20b"


def _number_code_lines(code: str) -> str:
    """Return code with 1-based line numbers for LLM referencing."""
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def build_parser_schema() -> dict:
    """Build the JSON schema used for structured output."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "nl_snippet": {"type": "string"},
                        "model_lines": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                            },
                            "required": ["start", "end"],
                        },
                        "code_excerpt": {"type": "string"},
                        "variables": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["nl_snippet", "model_lines", "code_excerpt", "confidence"],
                },
            },
            "unmapped_nl": {
                "type": "array",
                "items": {"type": "string"},
            },
            "unmapped_model_segments": {
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
                        "code_excerpt": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["model_lines", "code_excerpt"],
                },
            },
        },
        "required": ["mappings"],
    }


def build_parser_prompt(
    base_nl_description: str,
    numbered_model: str,
    schema: dict,
) -> str:
    schema_text = json.dumps(schema, indent=2)
    return f"""
You are the Parser agent for constraint-programming models. Your goal is to align a natural language problem description with an existing CPMPy model by pinpointing which sections of code implement each NL statement.

Produce a JSON object following this schema (also passed as the structured format):
{schema_text}

Guidelines:
- Use 1-based line numbers from the numbered model listing below.
- Keep code excerpts short (just the lines that implement the NL statement).
- Add brief reasoning and set lower confidence when unsure; never invent code or lines that are not present.
- If a NL requirement is not represented in the code, put it in 'unmapped_nl'.
- If code appears without a NL rationale, add it to 'unmapped_model_segments'.

Base NL description:
{base_nl_description}

CPMPy model with line numbers:
{numbered_model}
"""


def run_parser_agent(
    problem_path: str,
    base_desc_filename: str = "problem_desc.txt",
    base_model_filename: str = "reference_model.py",
    output_path: str | None = None,
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> tuple[dict, Path]:
    problem_dir = Path(problem_path)
    base_dir = problem_dir / "base"

    desc_path = base_dir / base_desc_filename
    model_path = base_dir / base_model_filename

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing base description at {desc_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing base model at {model_path}")

    base_nl_description = desc_path.read_text()
    base_model_code = model_path.read_text()
    numbered_model = _number_code_lines(base_model_code)

    schema = build_parser_schema()
    prompt = build_parser_prompt(base_nl_description, numbered_model, schema)

    response = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": "You map NL descriptions to CPMPy constraint code using line numbers."},
            {"role": "user", "content": prompt},
        ],
        format=schema,
        options={"temperature": temperature},
    )

    raw_content = response["message"]["content"]
    try:
        parsed_output = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}\nRaw content: {raw_content}") from exc

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if output_path is None:
        output_file = base_dir / f"{problem_dir.name}_parser_{timestamp}.json"
    else:
        output_file = Path(output_path)
        if not output_file.is_absolute():
            output_file = base_dir / output_file

    payload = {
        "problem": problem_dir.name,
        "base_desc": str(desc_path),
        "base_model": str(model_path),
        "timestamp": timestamp,
        "llm_model": model_name,
        "parser_output": parsed_output,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, indent=2))

    return parsed_output, output_file


def main():
    parser = argparse.ArgumentParser(
        description="Parser agent: map NL description to CPMPy model constraints with structured JSON output."
    )
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
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
        help="Optional output JSON path. Defaults to base/<problem>_parser_<timestamp>.json.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature passed to the LLM for determinism (default: 0.0).",
    )

    args = parser.parse_args()
    parsed_output, output_file = run_parser_agent(
        problem_path=args.problem,
        base_desc_filename=args.base_desc,
        base_model_filename=args.base_model,
        output_path=args.output,
        model_name=args.model_name,
        temperature=args.temperature,
    )

    print(f"Parser agent completed. Saved structured mapping to {output_file}")
    print(f"Found {len(parsed_output.get('mappings', []))} mappings.")


if __name__ == "__main__":
    main()
