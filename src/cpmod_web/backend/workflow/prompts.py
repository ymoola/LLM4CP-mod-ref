from __future__ import annotations

import json
from typing import Any

from ..services.execution.harness import execution_contract_text


def number_code_lines(code: str) -> str:
    return "\n".join(f"{idx + 1:04d}: {line}" for idx, line in enumerate(code.splitlines()))


def render_change_request(change_request: dict[str, Any]) -> str:
    payload = {
        "what_should_change": change_request.get("what_should_change"),
        "what_must_stay_the_same": change_request.get("what_must_stay_the_same"),
        "additional_detail": change_request.get("additional_detail"),
    }
    payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
    return json.dumps(payload, indent=2)


def render_metadata(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata or {}, indent=2)


def render_input_semantics(
    *,
    metadata: dict[str, Any],
    change_request: dict[str, Any],
) -> str:
    base_info = metadata.get("input_value_info")
    override_info = change_request.get("override_input_value_info")
    parts = [
        f"Base input field guide:\n{base_info or 'No base input field guide provided.'}",
    ]
    if override_info:
        parts.append(
            "Override input notes:\n"
            f"{override_info}\n"
            "If the override notes conflict with the base input field guide, trust the override notes for this run."
        )
    return "\n\n".join(parts)


def render_clarification_context(
    transcript: list[dict[str, Any]] | None,
    clarified_summary: str | None,
) -> str:
    parts: list[str] = []
    if clarified_summary:
        parts.append(
            "Authoritative clarified CR interpretation (use this if it conflicts with the raw CR wording):\n"
            f"{clarified_summary}"
        )
    if transcript:
        parts.append(
            "Clarification transcript between the workflow and the human:\n"
            f"{json.dumps(transcript, indent=2)}"
        )
    return "\n\n".join(parts) if parts else "No additional clarification context."


def render_runtime_input(
    *,
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
) -> str:
    source_label = "change request override input_data.json" if runtime_input_source == "change_request_override" else "base model package input_data.json"
    return (
        f"Runtime input source: {source_label}\n"
        f"Runtime input filename: {runtime_input_filename or 'input_data.json'}\n"
        "This runtime input is shown so you can understand field names, shapes, and expected instance structure. "
        "Do NOT hard-code these values into the generated model.\n"
        f"Effective runtime input JSON:\n{json.dumps(input_data, indent=2)}"
    )


def build_parser_prompt(
    *,
    problem_description: str,
    numbered_model: str,
    metadata: dict[str, Any],
    schema: dict[str, Any],
) -> str:
    schema_text = json.dumps(schema, indent=2)
    return f"""
You are the Parser agent for constraint-programming models. Your goal is to align an uploaded natural-language problem description with an existing CPMpy model by pinpointing which sections of code implement each NL statement.

Produce a JSON object following this schema (also passed as the structured format):
{schema_text}

Guidelines:
- Use 1-based line numbers from the numbered model listing below.
- Keep code excerpts short (just the lines that implement the NL statement).
- Add brief reasoning and set lower confidence when unsure; never invent code or lines that are not present.
- If a NL requirement is not represented in the code, put it in 'unmapped_nl'.
- If code appears without a NL rationale, add it to 'unmapped_model_segments'.
- Always include the keys 'mappings', 'unmapped_nl', and 'unmapped_model_segments' (use empty arrays if none).

Base problem description (NL):
{problem_description}

Uploaded model metadata:
{render_metadata(metadata)}

CPMpy model with line numbers:
{numbered_model}
"""


def build_clarification_assessor_prompt(
    *,
    problem_description: str,
    change_request: dict[str, Any],
    parser_output: dict[str, Any],
    metadata: dict[str, Any],
    schema: dict[str, Any],
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
    transcript: list[dict[str, Any]] | None = None,
) -> str:
    return f"""
You are the Clarification Assessor agent for a CPMpy change-request workflow.

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
- When status is "needs_clarification", keep clarified_request_summary empty and provide 1 to 3 concise questions.
- When status is "proceed", questions must be empty and clarified_request_summary must provide a short normalized interpretation that downstream agents can treat as authoritative.
- Do not ask for information already stated in the CR or transcript.
- Focus only on Change Request interpretation, not on coding style or solver details.

Base problem description (NL):
{problem_description}

Change Request JSON:
{render_change_request(change_request)}

Uploaded model metadata:
{render_metadata(metadata)}

Parser mapping:
{json.dumps(parser_output, indent=2)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Clarification transcript so far:
{json.dumps(transcript or [], indent=2)}
"""


def build_planner_prompt(
    *,
    problem_description: str,
    change_request: dict[str, Any],
    metadata: dict[str, Any],
    parser_output: dict[str, Any],
    numbered_model: str,
    schema: dict[str, Any],
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
    transcript: list[dict[str, Any]] | None = None,
    clarified_summary: str | None = None,
    previous_plan: dict[str, Any] | None = None,
    feedback: str | None = None,
) -> str:
    prompt = f"""
You are the Planner agent. Given a Change Request (CR) and the existing CPMpy model, produce a precise edit plan indicating what needs to change and where.

Output must follow this JSON schema (also enforced via structured output):
{json.dumps(schema, indent=2)}

Guidelines:
- Use 1-based line numbers from the numbered model listing.
- Prefer pointing to existing constraints or functions to modify; if adding, suggest a nearby line to insert after.
- Keep strategy concise but actionable for the Modifier agent (no full code, just how to implement).
- Do NOT propose changes unrelated to the CR; highlight sections to preserve so the modifier avoids regressions.
- If confidence is low, note risks.
- If you cannot confidently point to a location, set target_lines and/or insert_after_line to null rather than guessing.

Base problem description (NL):
{problem_description}

Change Request JSON:
{render_change_request(change_request)}

Clarification context:
{render_clarification_context(transcript, clarified_summary)}

Uploaded model metadata:
{render_metadata(metadata)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Parser mapping (NL to code):
{json.dumps(parser_output, indent=2)}

Numbered CPMPy reference model:
{numbered_model}
"""
    if previous_plan or feedback:
        prompt += f"""

Previous planner output:
{json.dumps(previous_plan or {}, indent=2)}

Planner validator feedback:
{feedback or '(none)'}
"""
    return prompt


def build_planner_validator_prompt(
    *,
    problem_description: str,
    change_request: dict[str, Any],
    metadata: dict[str, Any],
    parser_output: dict[str, Any],
    planner_output: dict[str, Any],
    numbered_model: str,
    schema: dict[str, Any],
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
    transcript: list[dict[str, Any]] | None = None,
    clarified_summary: str | None = None,
) -> str:
    return f"""
You are the Planner Validator agent. Review the planner output before any code is generated.

Your job:
- Check whether the plan fully covers the Change Request (CR).
- Check whether the target lines are plausible given the parser mapping and base model.
- Check whether the plan protects unaffected sections instead of proposing unnecessary changes.
- Do NOT write code and do NOT run code.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Guidelines:
- Return status "pass" only if the plan is specific, aligned with the CR, and safe for the modifier to execute.
- Return status "needs_changes" if the plan is missing a required edit, targets the wrong code, proposes unnecessary edits, or leaves preservation risks.
- Keep feedback concise and directly actionable for the Planner agent.
- Use 1-based line numbers when pointing to issues in the base model.
- If an issue cannot be localized to exact lines, set target_lines to null.

Base problem description (NL):
{problem_description}

Change Request JSON:
{render_change_request(change_request)}

Clarification context:
{render_clarification_context(transcript, clarified_summary)}

Uploaded model metadata:
{render_metadata(metadata)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Parser mapping:
{json.dumps(parser_output, indent=2)}

Planner output:
{json.dumps(planner_output, indent=2)}

Reference model with line numbers:
{numbered_model}
"""


def build_modifier_prompt(
    *,
    problem_description: str,
    base_model_code: str,
    numbered_model: str,
    change_request: dict[str, Any],
    metadata: dict[str, Any],
    plan: dict[str, Any],
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_summary: str | None = None,
    previous_code: str | None = None,
    feedback: str | None = None,
) -> str:
    prompt = f"""
You are the Modifier agent. Apply the Change Request (CR) to the CPMpy reference model with minimal edits, following the planner instructions.
Preserve existing constraints unless a planner step says to change them. Do not remove functionality unrelated to the CR.
Only output valid Python CPMpy code NOT SURROUNDED BY MARKDOWN OR BACKTICKS.

Base problem description (NL):
{problem_description}

Change Request JSON:
{render_change_request(change_request)}

Clarification context:
{render_clarification_context(clarification_transcript, clarified_summary)}

Uploaded model metadata:
{render_metadata(metadata)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Planner edit plan (authoritative):
{json.dumps(plan, indent=2)}

Reference CPMPy model (without line numbers):
{base_model_code}

Reference CPMPy model with line numbers:
{numbered_model}

Requirements:
- Respect this execution contract:
{execution_contract_text(metadata)}
- Preserve the key names and assumptions described in the metadata unless the CR explicitly changes them.
- Do NOT hard-code instance data, even though effective runtime input is shown above.
- Make the smallest safe set of edits necessary.
- Output valid Python CPMpy code only; no markdown, no extra text.

Formatting rules:
- Output ONLY valid Python CPMpy code.
- Do NOT include markdown, backticks, or explanations.
- If comments are needed, include only Python comments.
"""
    if previous_code or feedback:
        prompt += f"""

Previous attempt code:
{previous_code or '(none)'}

Feedback / error to address:
{feedback or '(none)'}
"""
    return prompt


def build_validator_prompt(
    *,
    problem_description: str,
    base_model_code: str,
    generated_model_code: str,
    change_request: dict[str, Any],
    metadata: dict[str, Any],
    schema: dict[str, Any],
    input_data: dict[str, Any],
    runtime_input_source: str | None,
    runtime_input_filename: str | None,
    clarification_transcript: list[dict[str, Any]] | None = None,
    clarified_summary: str | None = None,
) -> str:
    numbered_reference = number_code_lines(base_model_code)
    numbered_generated = number_code_lines(generated_model_code)
    return f"""
You are the Validator agent. Check whether the generated CPMpy model implements the Change Request (CR) correctly, without breaking existing behavior.
Do NOT run code. Rely only on the provided source texts.

Output must follow this JSON schema (also enforced via structured output):
{json.dumps(schema, indent=2)}

Guidelines:
- Use 1-based line numbers from the numbered listings.
- Flag only issues related to the CR or regressions to existing constraints, objectives, data handling, execution contract, or output interface.
- If everything aligns, return status "pass" and leave issues empty.
- If changes are needed, set status "needs_changes" and list concise issues with suggested fixes.
- Be strict about the execution contract and about preserving the important names described in the metadata.
- Be strict about data handling: do not approve code that hard-codes instance data when the model should rely on runtime input.
- If you cannot localize an issue to exact lines, set generated_lines/reference_lines to null.

Base problem description (NL):
{problem_description}

Change Request JSON:
{render_change_request(change_request)}

Clarification context:
{render_clarification_context(clarification_transcript, clarified_summary)}

Uploaded model metadata:
{render_metadata(metadata)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Expected execution contract:
{execution_contract_text(metadata)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Reference CPMPy model (with line numbers):
{numbered_reference}

Generated CPMpy model (with line numbers):
{numbered_generated}
"""
