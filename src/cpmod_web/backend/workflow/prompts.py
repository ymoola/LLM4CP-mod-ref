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
        "objective_change": change_request.get("objective_change"),
        "expected_output_changes": change_request.get("expected_output_changes"),
        "additional_detail": change_request.get("additional_detail"),
    }
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
        parts.append(f"Clarified request summary:\n{clarified_summary}")
    if transcript:
        parts.append(f"Clarification transcript:\n{json.dumps(transcript, indent=2)}")
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
        f"Effective runtime input JSON:\n{json.dumps(input_data, indent=2)}"
    )


def build_parser_prompt(
    *,
    problem_description: str,
    numbered_model: str,
    metadata: dict[str, Any],
    schema: dict[str, Any],
) -> str:
    return f"""
You are the Parser stage for a CPMpy model-modification workflow.
Map the uploaded natural-language problem description to the uploaded CPMpy model so later stages know where key semantics live.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Uploaded problem description:
{problem_description}

Required metadata:
{render_metadata(metadata)}

Numbered CPMpy model:
{numbered_model}
"""


def build_clarification_assessor_prompt(
    *,
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
Decide whether the user's change request is sufficiently clear to plan safely.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Change request:
{render_change_request(change_request)}

Uploaded metadata:
{render_metadata(metadata)}

Parser output:
{json.dumps(parser_output, indent=2)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Existing clarification transcript:
{json.dumps(transcript or [], indent=2)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Ask at most 3 clarification questions. Prefer proceeding if the ambiguity is low risk.
"""


def build_planner_prompt(
    *,
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
You are the Planner stage for a CPMpy model modification workflow.
Produce a precise, minimal edit plan for implementing the requested change while preserving unaffected behavior.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Change request:
{render_change_request(change_request)}

Uploaded metadata:
{render_metadata(metadata)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Parser output:
{json.dumps(parser_output, indent=2)}

Clarification context:
{render_clarification_context(transcript, clarified_summary)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Numbered base model:
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
Review the planner output before code generation.
Ensure the plan covers the change request, targets plausible locations, and preserves unaffected behavior.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Change request:
{render_change_request(change_request)}

Uploaded metadata:
{render_metadata(metadata)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Parser output:
{json.dumps(parser_output, indent=2)}

Clarification context:
{render_clarification_context(transcript, clarified_summary)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Planner output:
{json.dumps(planner_output, indent=2)}

Numbered base model:
{numbered_model}
"""


def build_modifier_prompt(
    *,
    base_model_code: str,
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
You are the Modifier stage for a CPMpy model-modification workflow.
Modify the uploaded base model to satisfy the change request while preserving unaffected behavior.

Return ONLY a complete Python file. No markdown. No explanation.

Base model:
{base_model_code}

Change request:
{render_change_request(change_request)}

Uploaded metadata:
{render_metadata(metadata)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Clarification context:
{render_clarification_context(clarification_transcript, clarified_summary)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

Planner output:
{json.dumps(plan, indent=2)}

Hard requirements:
- Respect this execution contract:
{execution_contract_text(metadata)}
- Preserve the key names and assumptions described in the metadata unless the change request explicitly changes them.
- Make the smallest safe set of edits necessary.
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
    return f"""
You are the final semantic validator for a CPMpy model-modification workflow.
Compare the generated model against the uploaded base model and the structured change request.
Do not execute code.

Output must follow this JSON schema:
{json.dumps(schema, indent=2)}

Base model:
{base_model_code}

Generated model:
{generated_model_code}

Change request:
{render_change_request(change_request)}

Uploaded metadata:
{render_metadata(metadata)}

Expected execution contract:
{execution_contract_text(metadata)}

Effective runtime input:
{render_runtime_input(input_data=input_data, runtime_input_source=runtime_input_source, runtime_input_filename=runtime_input_filename)}

Clarification context:
{render_clarification_context(clarification_transcript, clarified_summary)}

Input semantics:
{render_input_semantics(metadata=metadata, change_request=change_request)}

If the generated model appears executable but still has unresolved semantic concerns, return status needs_changes.
"""
