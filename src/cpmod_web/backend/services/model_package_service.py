from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from ..config import get_settings
from ..db import queries
from ..models.domain import ArtifactType, ExecutionResult, FailureType
from .execution.harness import execution_mode_from_metadata
from .execution.factory import get_execution_backend
from .storage_service import StorageService


def _parse_key_names(raw: str) -> list[str]:
    raw = (raw or '').strip()
    if not raw:
        return []
    if raw.startswith('['):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError('key_names_to_preserve must be a JSON list or comma-separated string.')
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in raw.split(',') if part.strip()]


def _default_solver_assumptions(*, execution_mode: str, entrypoint_name: str | None) -> str:
    if execution_mode == 'build_model':
        return f'The uploaded model is a module exposing `{entrypoint_name or "build_model"}` and should remain importable and solvable with values from input_data.json.'
    return 'The uploaded model is a standalone script that reads input_data.json and emits JSON to stdout.'


def _default_input_value_info(input_data: Any) -> str | None:
    if isinstance(input_data, dict):
        keys = [str(key) for key in input_data.keys()]
        if keys:
            return f"Top-level input_data.json fields: {', '.join(keys)}."
    return None


def _trim_block(text: str, *, limit: int = 600) -> str:
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '...'


def _build_validation_failure_summary(execution: ExecutionResult) -> str:
    if execution.error_type == FailureType.OUTPUT_FORMAT:
        stdout_preview = _trim_block(execution.stdout)
        if stdout_preview:
            return (
                'Base model executed, but stdout was not valid JSON. '
                f'Expected a single JSON object on stdout. Output preview: {stdout_preview}'
            )
        return 'Base model executed, but stdout was not valid JSON. Expected a single JSON object on stdout.'

    if execution.error_type == FailureType.TIMEOUT:
        return f'Base model validation timed out after {execution.timeout_seconds} seconds.'

    stderr_preview = _trim_block(execution.stderr)
    stdout_preview = _trim_block(execution.stdout)

    if stderr_preview:
        return stderr_preview
    if stdout_preview:
        return stdout_preview
    return 'Base model validation failed.'


async def create_model_package_with_validation(
    *,
    project_id: str,
    model_file: UploadFile,
    description_file: UploadFile,
    input_data_file: UploadFile,
    execution_mode: str,
    entrypoint_name: str | None,
    output_variable_names: str | None,
    key_names_to_preserve: str | None,
    input_value_info: str | None,
) -> dict[str, Any]:
    if not model_file.filename or not model_file.filename.endswith('.py'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Model file must be a .py file.')
    if not description_file.filename or not description_file.filename.endswith('.txt'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Problem description must be a .txt file.')
    if not input_data_file.filename or not input_data_file.filename.endswith('.json'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Input data must be a .json file.')

    key_names = _parse_key_names(key_names_to_preserve or '')
    output_names = _parse_key_names(output_variable_names or '')

    normalized_execution_mode = execution_mode_from_metadata({'execution_mode': execution_mode})
    if normalized_execution_mode == 'build_model' and not output_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='build_model mode requires at least one output variable name.')

    entrypoint = (entrypoint_name or '').strip() or ('build_model' if normalized_execution_mode == 'build_model' else None)
    if not key_names:
        key_names = list(dict.fromkeys(output_names + ([entrypoint] if entrypoint else [])))

    try:
        input_data = json.loads((await input_data_file.read()).decode('utf-8'))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'input_data.json is not valid JSON: {exc}') from exc

    model_code = (await model_file.read()).decode('utf-8')
    problem_description = (await description_file.read()).decode('utf-8')
    metadata = {
        'execution_mode': normalized_execution_mode,
        'entrypoint_name': entrypoint,
        'output_variable_names': output_names,
        'key_names_to_preserve': key_names,
        'solver_assumptions': _default_solver_assumptions(execution_mode=normalized_execution_mode, entrypoint_name=entrypoint),
        'input_value_info': (input_value_info or '').strip() or _default_input_value_info(input_data),
    }

    package_id = str(uuid4())
    storage = StorageService()
    settings = get_settings()
    base_prefix = f'projects/{project_id}/model-packages/{package_id}'
    model_storage_path = storage.upload_text(bucket=settings.models_bucket, path=f'{base_prefix}/{model_file.filename}', content=model_code, content_type='text/x-python')
    description_storage_path = storage.upload_text(bucket=settings.models_bucket, path=f'{base_prefix}/{description_file.filename}', content=problem_description, content_type='text/plain')
    input_data_storage_path = storage.upload_json(bucket=settings.models_bucket, path=f'{base_prefix}/{input_data_file.filename}', payload=input_data)

    package = queries.create_model_package(
        {
            'id': package_id,
            'project_id': project_id,
            'filename': model_file.filename,
            'problem_description_filename': description_file.filename,
            'input_data_filename': input_data_file.filename,
            'model_storage_path': model_storage_path,
            'problem_description_storage_path': description_storage_path,
            'input_data_storage_path': input_data_storage_path,
            'metadata': metadata,
            'validation_status': 'running',
        }
    )

    try:
        executor = get_execution_backend()
        execution = await executor.execute_model(code=model_code, input_data=input_data, metadata=metadata)
        artifact_payload = execution.model_dump()
        artifact_path = storage.upload_json(
            bucket=settings.artifacts_bucket,
            path=f'model-packages/{package["id"]}/base_validation_log.json',
            payload=artifact_payload,
        )
        queries.add_run_artifact(
            {
                'run_id': None,
                'type': ArtifactType.BASE_VALIDATION_LOG.value,
                'storage_path': artifact_path,
                'metadata': {'model_package_id': package['id'], 'passed': execution.passed},
            }
        )

        if execution.passed:
            success_summary = 'Base model executed successfully and returned valid JSON.'
            if normalized_execution_mode == 'build_model':
                success_summary = 'Base model entrypoint executed successfully and serialized the configured outputs as JSON.'
            package = queries.update_model_package(
                package['id'],
                {
                    'validation_status': 'validated',
                    'validation_summary': success_summary,
                },
            )
        else:
            message = _build_validation_failure_summary(execution)
            package = queries.update_model_package(
                package['id'],
                {
                    'validation_status': 'failed',
                    'validation_summary': message,
                },
            )
        return package
    except Exception as exc:
        message = f'Unexpected validation error: {type(exc).__name__}: {exc}'
        package = queries.update_model_package(
            package['id'],
            {
                'validation_status': 'failed',
                'validation_summary': message,
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc
