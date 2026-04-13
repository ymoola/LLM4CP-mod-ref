from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..db import queries
from ..models.domain import ArtifactType, EventOutcome, FailureType, RunStatus
from ..services.diff_service import build_unified_diff
from ..services.execution.factory import get_execution_backend
from ..services.llm_service import LLMService, get_model_config
from ..services.storage_service import StorageService
from .graph import build_graph
from .state import WorkflowState


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProductWorkflowRuntime:
    run: dict[str, Any]
    change_request: dict[str, Any]
    model_package: dict[str, Any]
    storage: StorageService
    llm: LLMService
    executor: Any

    def log_stage(self, stage: str, outcome: str, *, attempt: int = 1, message: str | None = None, failure_type: str | None = None, payload: dict[str, Any] | None = None) -> None:
        queries.add_run_event(
            {
                'run_id': self.run['id'],
                'stage': stage,
                'outcome': outcome,
                'failure_type': failure_type,
                'message': message,
                'attempt': attempt,
                'payload': payload or {},
            }
        )

    def _artifact_storage_path(self, artifact_type: ArtifactType, filename: str) -> str:
        return f"runs/{self.run['id']}/{artifact_type.value}/{filename}"

    def save_artifact_text(self, *, artifact_type: ArtifactType, filename: str, content: str, metadata: dict[str, Any] | None = None, content_type: str = 'text/plain') -> str:
        storage_path = self._artifact_storage_path(artifact_type, filename)
        self.storage.upload_text(bucket=get_settings().artifacts_bucket, path=storage_path, content=content, content_type=content_type)
        queries.add_run_artifact(
            {
                'run_id': self.run['id'],
                'type': artifact_type.value,
                'storage_path': storage_path,
                'metadata': metadata or {},
            }
        )
        return storage_path

    def save_generated_model(self, *, code: str, attempt: int) -> str:
        return self.save_artifact_text(
            artifact_type=ArtifactType.GENERATED_MODEL,
            filename=f'generated_model_attempt_{attempt}.py',
            content=code,
            metadata={'attempt': attempt},
            content_type='text/x-python',
        )

    def save_execution_log(self, *, result: Any, attempt: int) -> str:
        return self.save_artifact_text(
            artifact_type=ArtifactType.EXECUTION_LOG,
            filename=f'execution_attempt_{attempt}.json',
            content=json.dumps(result.model_dump(), indent=2),
            metadata={'attempt': attempt, 'passed': result.passed},
            content_type='application/json',
        )

    def save_validator_report(self, *, output: dict[str, Any], attempt: int) -> str:
        return self.save_artifact_text(
            artifact_type=ArtifactType.VALIDATOR_REPORT,
            filename=f'validator_attempt_{attempt}.json',
            content=json.dumps(output, indent=2),
            metadata={'attempt': attempt, 'status': output.get('status')},
            content_type='application/json',
        )

    def cache_parser_output(self, parser_output: dict[str, Any]) -> None:
        queries.update_model_package(self.model_package['id'], {'parser_output': parser_output})
        self.model_package['parser_output'] = parser_output

    def persist_pause(self, *, state: WorkflowState, questions: list[str]) -> None:
        queries.update_workflow_run(
            self.run['id'],
            {
                'status': RunStatus.AWAITING_CLARIFICATION.value,
                'clarification_questions': questions,
                'state_json': state,
                'resume_from_stage': 'planning',
            },
        )

    def finalize_run(self, *, state: WorkflowState, final_status: str, failure_type: str | None) -> None:
        if state.get('generated_code'):
            diff = build_unified_diff(before=state['base_model_code'], after=state['generated_code'])
            self.save_artifact_text(
                artifact_type=ArtifactType.DIFF,
                filename='generated_model.diff',
                content=diff,
                metadata={'final_status': final_status},
                content_type='text/plain',
            )
        queries.update_workflow_run(
            self.run['id'],
            {
                'status': final_status,
                'completed_at': _utcnow_iso(),
                'failure_type': failure_type,
                'last_error': state.get('execution_error') or state.get('validator_feedback') or None,
                'change_summary': state.get('change_summary'),
                'invariants': state.get('invariants'),
                'state_json': state,
                'resume_from_stage': None,
            },
        )


def _load_model_package_assets(model_package: dict[str, Any], storage: StorageService) -> tuple[str, str, dict[str, Any]]:
    settings = get_settings()
    base_model_code = storage.download_text(bucket=settings.models_bucket, path=model_package['model_storage_path'])
    problem_description = storage.download_text(bucket=settings.models_bucket, path=model_package['problem_description_storage_path'])
    input_data = json.loads(storage.download_text(bucket=settings.models_bucket, path=model_package['input_data_storage_path']))
    return base_model_code, problem_description, input_data


def _load_effective_runtime_input(
    *,
    change_request: dict[str, Any],
    model_package: dict[str, Any],
    storage: StorageService,
) -> tuple[dict[str, Any], str, str]:
    settings = get_settings()
    if change_request.get('override_input_data_storage_path'):
        input_data = json.loads(
            storage.download_text(bucket=settings.models_bucket, path=change_request['override_input_data_storage_path'])
        )
        return (
            input_data,
            'change_request_override',
            change_request.get('override_input_data_filename') or model_package.get('input_data_filename') or 'input_data.json',
        )
    base_input_data = json.loads(storage.download_text(bucket=settings.models_bucket, path=model_package['input_data_storage_path']))
    return base_input_data, 'base', model_package.get('input_data_filename') or 'input_data.json'


def _merge_resume_state(run: dict[str, Any]) -> WorkflowState:
    state = dict(run.get('state_json') or {})
    answers = run.get('clarification_answers') or []
    questions = run.get('clarification_questions') or []
    transcript = list(state.get('clarification_transcript') or [])
    if answers:
        transcript.append({'questions': questions, 'answers': answers})
    state['clarification_answers'] = answers
    state['clarification_questions'] = questions
    state['clarification_transcript'] = transcript
    return state


async def run_workflow(run_id: str) -> dict[str, Any]:
    run = queries.get_workflow_run(run_id)
    if not run:
        raise ValueError(f'Workflow run {run_id} does not exist.')
    change_request = queries.get_change_request(run['change_request_id'])
    if not change_request:
        raise ValueError(f'Change request {run["change_request_id"]} does not exist.')
    model_package = queries.get_model_package(change_request['model_package_id'])
    if not model_package:
        raise ValueError(f'Model package {change_request["model_package_id"]} does not exist.')

    storage = StorageService()
    llm = LLMService(get_model_config(run['model_config']))
    executor = get_execution_backend()
    runtime = ProductWorkflowRuntime(run=run, change_request=change_request, model_package=model_package, storage=storage, llm=llm, executor=executor)

    if run.get('resume_from_stage'):
        state: WorkflowState = _merge_resume_state(run)
        start_node = run['resume_from_stage']
    else:
        base_model_code, problem_description, _ = _load_model_package_assets(model_package, storage)
        input_data, runtime_input_source, runtime_input_filename = _load_effective_runtime_input(
            change_request=change_request,
            model_package=model_package,
            storage=storage,
        )
        state = {
            'run_id': run['id'],
            'model_package_id': model_package['id'],
            'change_request_id': change_request['id'],
            'base_model_code': base_model_code,
            'problem_description': problem_description,
            'input_data': input_data,
            'runtime_input_source': runtime_input_source,
            'runtime_input_filename': runtime_input_filename,
            'metadata': model_package.get('metadata') or {},
            'change_request': change_request,
            'clarification_transcript': [],
            'planner_validation_attempts': 0,
            'max_planner_validation_loops': get_settings().max_planner_validation_loops,
            'execution_attempts': 0,
            'max_execution_loops': get_settings().max_execution_loops,
            'validator_attempts': 0,
            'max_validator_loops': get_settings().max_validator_loops,
        }
        start_node = 'parsing'
        queries.update_workflow_run(run['id'], {'status': RunStatus.IN_PROGRESS.value, 'started_at': run.get('started_at') or _utcnow_iso()})

    graph = build_graph(runtime, start_node=start_node)
    result = await graph.ainvoke(state)
    if result.get('final_status') == 'awaiting_clarification':
        return result
    if result.get('final_status') in {RunStatus.COMPLETED.value, RunStatus.NEEDS_REVIEW.value, RunStatus.FAILED.value}:
        return result
    runtime.finalize_run(state=result, final_status=RunStatus.FAILED.value, failure_type=FailureType.INTERNAL_ERROR.value)
    return result
