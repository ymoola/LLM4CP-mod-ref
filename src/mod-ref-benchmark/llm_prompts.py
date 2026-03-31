from __future__ import annotations

import json
import re
from typing import Any


def number_code_lines(code: str) -> str:
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def extract_output_keys(ref_sol_format: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for _, spec in (ref_sol_format or {}).items():
        descr = (spec or {}).get("descr", "") or ""
        match = re.search(r"`([^`]+)`", descr)
        if not match:
            continue
        name = match.group(1).strip()
        if name.endswith(":"):
            name = name[:-1].strip()
        if name and name not in keys:
            keys.append(name)
    return keys


def strip_complexity_metadata(cr_desc: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(cr_desc or {})
    sanitized.pop("complexity", None)
    return sanitized


def render_clarification_context(
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_cr_summary: str | None = None,
) -> str:
    transcript = clarification_transcript or []
    summary = (clarified_cr_summary or "").strip()
    if not transcript and not summary:
        return "No additional clarification context."

    parts: list[str] = []
    if summary:
        parts.append(
            "Authoritative clarified CR interpretation (use this if it conflicts with the raw CR wording):\n"
            f"{summary}"
        )
    if transcript:
        parts.append(
            "Clarification transcript between the workflow and the human:\n"
            f"{json.dumps(transcript, indent=2)}"
        )
    return "\n\n".join(parts)


def build_parser_prompt(base_nl_description: str, numbered_model: str, schema: dict[str, Any]) -> str:
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
- Always include the keys 'mappings', 'unmapped_nl', and 'unmapped_model_segments' (use empty arrays if none).

Base NL description:
{base_nl_description}

CPMPy model with line numbers:
{numbered_model}
"""


def build_planner_prompt(
    base_nl_description: str,
    cr_desc: dict[str, Any],
    numbered_model: str,
    parser_mapping: dict[str, Any],
    schema: dict[str, Any],
    previous_plan: dict[str, Any] | None = None,
    feedback: str | None = None,
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_cr_summary: str | None = None,
) -> str:
    prompt_cr_desc = strip_complexity_metadata(cr_desc)
    clarification_context = render_clarification_context(
        clarification_transcript=clarification_transcript,
        clarified_cr_summary=clarified_cr_summary,
    )
    prompt = f"""
You are the Planner agent. Given a change request (CR) and the existing CPMPy model, produce a precise edit plan indicating what needs to change (add/modify constraints or objectives) and where.

Output must follow this JSON schema (also enforced via structured output):
{json.dumps(schema, indent=2)}

Guidelines:
- Use 1-based line numbers from the numbered model listing.
- Prefer pointing to existing constraints to modify; if adding, suggest nearby line to insert (insert_after_line).
- Keep strategy concise but actionable for the Modifier agent (no full code, just how to implement).
- Do NOT propose changes unrelated to the CR; highlight sections to preserve so the modifier avoids regressions.
- If confidence is low, note risks.
- If you cannot confidently point to a location, set target_lines to null and/or insert_after_line to null (do not guess line numbers).

Change Request (CR) JSON:
{json.dumps(prompt_cr_desc, indent=2)}

Clarification context:
{clarification_context}

Base problem description (NL):
{base_nl_description}

Parser mapping (NL to code):
{json.dumps(parser_mapping, indent=2)}

Numbered CPMPy reference model:
{numbered_model}
"""
    if previous_plan or feedback:
        prompt += f"""

Previous planner output:
{json.dumps(previous_plan or {}, indent=2)}

Planner validator feedback:
{feedback or "(none)"}

Revise the plan to address the feedback while keeping correct parts of the existing plan.
"""
    return prompt


def build_planner_validator_prompt(
    base_nl_description: str,
    cr_desc: dict[str, Any],
    parser_mapping: dict[str, Any],
    planner_output: dict[str, Any],
    numbered_model: str,
    schema: dict[str, Any],
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_cr_summary: str | None = None,
) -> str:
    prompt_cr_desc = strip_complexity_metadata(cr_desc)
    clarification_context = render_clarification_context(
        clarification_transcript=clarification_transcript,
        clarified_cr_summary=clarified_cr_summary,
    )
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
{json.dumps(prompt_cr_desc, indent=2)}

Clarification context:
{clarification_context}

Parser mapping:
{json.dumps(parser_mapping, indent=2)}

Planner output to review:
{json.dumps(planner_output, indent=2)}

Reference model with line numbers:
{numbered_model}
"""


def build_modifier_prompt(
    base_nl_description: str,
    cr_desc: dict[str, Any],
    planner_plan: dict[str, Any],
    base_model_code: str,
    numbered_model: str,
    previous_code: str | None,
    error_message: str | None,
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_cr_summary: str | None = None,
) -> str:
    cr_text = cr_desc.get("content", "")
    value_info = cr_desc.get("value_info", [])
    ref_sol_format = cr_desc.get("ref_sol_format", {})
    expected_output_keys = extract_output_keys(ref_sol_format)
    clarification_context = render_clarification_context(
        clarification_transcript=clarification_transcript,
        clarified_cr_summary=clarified_cr_summary,
    )

    prompt = f"""
You are the Modifier agent. Apply the change request to the CPMPy reference model with minimal edits, following the planner instructions. 
Preserve existing constraints unless a planner step says to change them. Do not remove functionality unrelated to the CR. Only ouput valid Python CPMPy code NOT SURROUNDED BY MARKDOWN OR BACKTICKS.

Base problem description (NL):
{base_nl_description}

Change Request (content):
{cr_text}

Clarification context:
{clarification_context}

Parameter description (value_info):
{json.dumps(value_info, indent=2)}

Expected output format (ref_sol_format):
{json.dumps(ref_sol_format, indent=2)}

CRITICAL INSTRUCTION ABOUT OUTPUT KEYS:
- Keys like "var1", "var2", ... in ref_sol_format are ONLY placeholders.
- You MUST output the REAL keys, extracted from the backtick-quoted identifier in each ref_sol_format[*]["descr"] field.
- For this CR, the expected top-level JSON keys are: {expected_output_keys}
- Example: if descr contains "`sequence`:", the output JSON must contain the key "sequence" (NOT "var1").

Planner edit plan (authoritative):
{json.dumps(planner_plan, indent=2)}

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


def build_validator_prompt(
    base_nl_description: str,
    cr_desc: dict[str, Any],
    reference_model_code: str,
    generated_model_code: str,
    numbered_reference: str,
    numbered_generated: str,
    schema: dict[str, Any],
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_cr_summary: str | None = None,
) -> str:
    cr_text = cr_desc.get("content", "")
    expected_output_keys = extract_output_keys(cr_desc.get("ref_sol_format", {}))
    clarification_context = render_clarification_context(
        clarification_transcript=clarification_transcript,
        clarified_cr_summary=clarified_cr_summary,
    )
    return f"""
You are the Validator agent. Check whether the generated CPMPy model implements the Change Request (CR) correctly, without breaking existing behavior.

Do NOT run code. Rely only on the provided source texts.

Output must follow this JSON schema (also enforced via structured output):
{json.dumps(schema, indent=2)}

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

Clarification context:
{clarification_context}

Parameter description (value_info):
{json.dumps(cr_desc.get("value_info", []), indent=2)}

Expected output format (ref_sol_format):
{json.dumps(cr_desc.get("ref_sol_format", {}), indent=2)}

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


def build_clarification_assessor_prompt(
    *,
    base_nl_description: str,
    cr_desc: dict[str, Any],
    parser_mapping: dict[str, Any],
    schema: dict[str, Any],
    clarification_transcript: list[dict[str, Any]] | None = None,
) -> str:
    prompt_cr_desc = strip_complexity_metadata(cr_desc)
    transcript = clarification_transcript or []
    return f"""
You are the Clarification Assessor agent for a CPMPy change-request workflow.

Your job:
- Decide whether the Change Request (CR) is clear enough for the Planner agent to proceed safely.
- Ask clarifying questions only if ambiguity would materially change the model edits.
- Ask at most 3 concise questions.
- If prior human answers resolve the ambiguity, do NOT ask the same question again.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Decision rules:
- Return status "proceed" when the CR is clear enough to plan safely.
- Return status "needs_clarification" only when the ambiguity is material to implementation.
- When status is "needs_clarification", keep clarified_cr_summary empty and provide 1 to 3 concise questions.
- When status is "proceed", questions must be empty and clarified_cr_summary must provide a short normalized interpretation that downstream agents can treat as authoritative.
- Do not ask for information already stated in the CR or transcript.
- Focus only on CR interpretation, not on coding style or solver details.

Base problem description:
{base_nl_description}

Change Request JSON:
{json.dumps(prompt_cr_desc, indent=2)}

Parser mapping:
{json.dumps(parser_mapping, indent=2)}

Clarification transcript so far:
{json.dumps(transcript, indent=2)}
"""


def build_single_shot_prompt(
    *,
    base_nl_description: str,
    base_reference_code: str,
    cr_desc: dict[str, Any],
    expected_output_keys: list[str],
) -> str:
    cr_text = cr_desc.get("content", "")
    value_info = cr_desc.get("value_info", [])
    ref_sol_format = cr_desc.get("ref_sol_format", {})
    prob_type = cr_desc.get("prob_type", "")

    return f"""
You are a CPMPy modeling assistant.

Task: Modify/extend the given *base* CPMPy reference model to implement the Change Request (CR), and output a COMPLETE, EXECUTABLE Python script.

This is a single-shot generation: you must do everything in one pass.

Inputs you can rely on at runtime:
- A file named input_data.json in the same directory as the generated script.

Requirements (very important):
- Use CPMPy (cpmpy) and json for I/O. Only use other standard libs if truly necessary.
- Load ALL numeric parameters ONLY from input_data.json. Do NOT hard-code instance data.
- Implement the CR precisely while preserving unrelated base constraints.
- The script must be self-contained: do NOT import local project files (e.g., reference_model.py). Copy/adapt any needed code directly.
- Solve the model (satisfaction or optimization as appropriate).
- Print EXACTLY ONE JSON object to stdout using print(json.dumps(...)).

CRITICAL INSTRUCTION ABOUT OUTPUT KEYS:
- In ref_sol_format, keys like "var1", "var2", ... are placeholders.
- The REAL output keys are the backtick-quoted identifiers inside each ref_sol_format[*].descr.
- For this CR, you MUST output a JSON dict with the following top-level keys:
  {expected_output_keys}

Return format:
- Output ONLY the Python code (no markdown, no backticks, no surrounding text).

Base problem description (NL):
{base_nl_description}

Change Request:
{cr_text}

Parameter description (value_info):
{json.dumps(value_info, indent=2)}

Expected output format (ref_sol_format) [placeholders like var1 are NOT real keys]:
{json.dumps(ref_sol_format, indent=2)}

Problem type hint (prob_type):
{prob_type}

Base CPMPy reference model code:
{base_reference_code}
"""
