from __future__ import annotations

from typing import Any, Literal, TypedDict


class WorkflowState(TypedDict, total=False):
    run_id: str
    model_package_id: str
    change_request_id: str
    base_model_code: str
    problem_description: str
    input_data: dict[str, Any]
    runtime_input_source: Literal['base', 'change_request_override']
    runtime_input_filename: str
    metadata: dict[str, Any]
    change_request: dict[str, Any]
    parser_output: dict[str, Any]
    clarification_status: Literal['proceed', 'needs_clarification']
    clarification_questions: list[str]
    clarification_answers: list[str]
    clarification_transcript: list[dict[str, Any]]
    clarified_request_summary: str
    planner_output: dict[str, Any]
    planner_feedback: str
    planner_validator_output: dict[str, Any]
    planner_validator_status: str
    planner_validation_attempts: int
    max_planner_validation_loops: int
    generated_code: str
    generated_model_artifact_path: str
    execution_output: dict[str, Any]
    execution_ok: bool
    execution_error: str
    execution_attempts: int
    max_execution_loops: int
    validator_output: dict[str, Any]
    validator_status: str
    validator_feedback: str
    validator_attempts: int
    max_validator_loops: int
    final_status: str
    failure_type: str
    change_summary: str
    invariants: dict[str, Any]
