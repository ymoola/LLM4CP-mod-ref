import argparse
import datetime
import json
import re
from pathlib import Path

from llm_client import LLMClient, LLMConfig


DEFAULT_MODEL = "gpt-oss:20b"


def _number_code_lines(code: str) -> str:
    """Return code with 1-based line numbers for LLM referencing."""
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))

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


def build_validator_schema() -> dict:
    """Schema for structured validator output."""
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
                                "missing_constraint",
                                "incorrect_constraint",
                                "objective",
                                "data_handling",
                                "output_format",
                                "style",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "generated_lines": {
                            "anyOf": [line_range_schema, {"type": "null"}],
                        },
                        "reference_lines": {
                            "anyOf": [line_range_schema, {"type": "null"}],
                        },
                        "suggestion": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                    },
                    "required": [
                        "title",
                        "description",
                        "category",
                        "severity",
                        "generated_lines",
                        "reference_lines",
                        "suggestion",
                        "confidence",
                    ],
                },
            },
            "notes_for_modifier": {"type": "string"},
        },
        "required": ["status", "summary", "issues", "notes_for_modifier"],
    }


def build_validator_prompt(
    base_nl_description: str,
    cr_desc: dict,
    reference_model_code: str,
    generated_model_code: str,
    numbered_reference: str,
    numbered_generated: str,
    schema: dict,
) -> str:
    cr_text = cr_desc.get("content", "")
    value_info = json.dumps(cr_desc.get("value_info", []), indent=2)
    ref_sol_format = json.dumps(cr_desc.get("ref_sol_format", {}), indent=2)
    expected_output_keys = extract_output_keys(cr_desc.get("ref_sol_format", {}))
    schema_text = json.dumps(schema, indent=2)

    return f"""
You are the Validator agent. Check whether the generated CPMPy model implements the Change Request (CR) correctly, without breaking existing behavior.

Do NOT run code. Rely only on the provided source texts.

Output must follow this JSON schema (also enforced via structured output):
{schema_text}

Guidelines:
- Use 1-based line numbers from the numbered listings.
- Flag only issues related to the CR or regressions to existing constraints/objective/output format.
- If everything aligns, return status "pass" and leave issues empty.
- If changes are needed, set status "needs_changes" and list concise issues with suggested fixes.
- Be strict about loading data (no hard-coded instance values) and respecting ref_sol_format variable names.
- If you cannot localize an issue to exact lines, set generated_lines/reference_lines to null.

Base problem description (NL):
{base_nl_description}

Change Request (content):
{cr_text}

Parameter description (value_info):
{value_info}

Expected output format (ref_sol_format):
{ref_sol_format}

CRITICAL INSTRUCTION ABOUT OUTPUT KEYS:
- Keys like "var1", "var2", ... in ref_sol_format are ONLY placeholders.
- The REAL output keys are the backtick-quoted identifiers in each ref_sol_format[*]["descr"] field.
- For this CR, the expected top-level JSON keys are: {expected_output_keys}
- Do NOT claim that the output should use "var1" if the descr indicates "`sequence`" (etc.).

Reference CPMPy model (with line numbers):
{numbered_reference}

Generated CPMPy model (with line numbers):
{numbered_generated}
"""


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

    numbered_reference = _number_code_lines(reference_model_code)
    numbered_generated = _number_code_lines(generated_model_code)

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
        model_name = "gpt-4o-mini"

    llm_config = {"provider": args.provider, "model": model_name}

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
