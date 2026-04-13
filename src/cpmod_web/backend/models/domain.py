from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    AWAITING_CLARIFICATION = 'awaiting_clarification'
    COMPLETED = 'completed'
    NEEDS_REVIEW = 'needs_review'
    FAILED = 'failed'


class RunStage(str, Enum):
    UPLOAD_VALIDATION = 'upload_validation'
    PARSING = 'parsing'
    CLARIFICATION_ASSESSMENT = 'clarification_assessment'
    CLARIFICATION_WAITING = 'clarification_waiting'
    PLANNING = 'planning'
    PLAN_VALIDATION = 'plan_validation'
    MODIFICATION = 'modification'
    EXECUTION = 'execution'
    SEMANTIC_VALIDATION = 'semantic_validation'
    FINALIZE = 'finalize'


class EventOutcome(str, Enum):
    STARTED = 'started'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    WAITING = 'waiting'


class FailureType(str, Enum):
    UPLOAD_VALIDATION = 'upload_validation'
    SYNTAX_ERROR = 'syntax_error'
    RUNTIME_ERROR = 'runtime_error'
    TIMEOUT = 'timeout'
    OUTPUT_FORMAT = 'output_format'
    PLANNER_REJECTED = 'planner_rejected'
    VALIDATION_REJECTED = 'validation_rejected'
    INTERNAL_ERROR = 'internal_error'


class ArtifactType(str, Enum):
    BASE_VALIDATION_LOG = 'base_validation_log'
    GENERATED_MODEL = 'generated_model'
    EXECUTION_LOG = 'execution_log'
    VALIDATOR_REPORT = 'validator_report'
    DIFF = 'diff'


class ExecutionResult(BaseModel):
    passed: bool
    stdout: str = ''
    stderr: str = ''
    exit_code: int = 0
    parsed_output: dict[str, Any] | None = None
    error_type: FailureType | None = None
    timeout_seconds: int | None = None


class InvariantsSummary(BaseModel):
    variables_preserved: list[str] = Field(default_factory=list)
    variables_added: list[str] = Field(default_factory=list)
    objective_changed: bool = False
    constraints_added: list[str] = Field(default_factory=list)
    constraints_modified: list[str] = Field(default_factory=list)
    constraints_removed: list[str] = Field(default_factory=list)
