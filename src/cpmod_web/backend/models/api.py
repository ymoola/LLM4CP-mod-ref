from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .domain import RunStatus


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    created_at: datetime | None = None


class ModelPackageRead(BaseModel):
    id: str
    project_id: str
    filename: str
    problem_description_filename: str
    input_data_filename: str
    validation_status: str
    validation_summary: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    parser_output: dict[str, Any] | None = None
    model_file_url: str | None = None
    problem_description_file_url: str | None = None
    input_data_file_url: str | None = None
    validation_log_url: str | None = None


class ChangeRequestRead(BaseModel):
    id: str
    project_id: str
    model_package_id: str
    model_package_filename: str | None = None
    override_input_data_filename: str | None = None
    override_input_data_file_url: str | None = None
    override_input_value_info: str | None = None
    what_should_change: str
    what_must_stay_the_same: str | None = None
    objective_change: str
    expected_output_changes: str | None = None
    additional_detail: str | None = None
    status: str
    created_at: datetime | None = None


class ModelCatalogEntryRead(BaseModel):
    id: str
    preset: Literal['fast', 'quality']
    provider: Literal['openai', 'openrouter']
    model_name: str
    label: str
    description: str
    reasoning_effort: Literal['none', 'minimal', 'low', 'medium', 'high'] | None = None
    max_output_tokens: int | None = None
    is_default: bool = False


class ProviderCredentialStatusRead(BaseModel):
    provider: Literal['openai', 'openrouter']
    has_key: bool
    updated_at: datetime | None = None


class RunCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    change_request_id: str
    model_preset: Literal['fast', 'quality'] = Field(default='quality', alias='model_config')
    model_provider: Literal['openai', 'openrouter']
    model_name: str
    api_key_provider: Literal['openai', 'openrouter']


class ClarificationSubmit(BaseModel):
    answers: list[str]


class RunArtifactRead(BaseModel):
    id: str
    run_id: str
    type: str
    storage_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    signed_url: str | None = None


class RunEventRead(BaseModel):
    id: str
    run_id: str
    stage: str
    outcome: str
    failure_type: str | None = None
    message: str | None = None
    attempt: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class RunRead(BaseModel):
    id: str
    change_request_id: str
    project_id: str | None = None
    model_package_id: str | None = None
    model_package_filename: str | None = None
    change_request_summary: str | None = None
    runtime_input_source: Literal['base', 'change_request_override'] | None = None
    runtime_input_filename: str | None = None
    runtime_input_file_url: str | None = None
    status: RunStatus
    model_preset: Literal['fast', 'quality']
    model_provider: Literal['openai', 'openrouter']
    model_name: str
    api_key_provider: Literal['openai', 'openrouter']
    credential_source: Literal['user_saved']
    clarification_questions: list[str] = Field(default_factory=list)
    clarification_answers: list[str] = Field(default_factory=list)
    invariants: dict[str, Any] | None = None
    change_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_type: str | None = None
    last_error: str | None = None
    created_at: datetime | None = None
    events: list[RunEventRead] = Field(default_factory=list)
    artifacts: list[RunArtifactRead] = Field(default_factory=list)


class RunSummaryRead(BaseModel):
    id: str
    change_request_id: str
    project_id: str | None = None
    model_package_id: str | None = None
    model_package_filename: str | None = None
    change_request_summary: str | None = None
    runtime_input_source: Literal['base', 'change_request_override'] | None = None
    status: RunStatus
    model_preset: Literal['fast', 'quality']
    model_provider: Literal['openai', 'openrouter']
    model_name: str
    api_key_provider: Literal['openai', 'openrouter']
    credential_source: Literal['user_saved']
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_type: str | None = None


class DashboardCountsRead(BaseModel):
    total_projects: int
    validated_model_packages: int
    completed_runs: int
    runs_needing_review: int
    failed_runs: int


class DashboardOverviewRead(BaseModel):
    counts: DashboardCountsRead
    recent_projects: list[ProjectRead] = Field(default_factory=list)
    recent_runs: list[RunSummaryRead] = Field(default_factory=list)
    runs_awaiting_clarification: list[RunSummaryRead] = Field(default_factory=list)
    runs_needing_review: list[RunSummaryRead] = Field(default_factory=list)
