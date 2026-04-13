from __future__ import annotations

from ..config import get_settings
from ..db import queries
from .model_catalog import infer_run_selection
from .storage_service import StorageService


def serialize_run(run: dict, *, include_details: bool = True) -> dict:
    storage = StorageService()
    settings = get_settings()
    change_request = queries.get_change_request(run['change_request_id'])
    model_package = queries.get_model_package(change_request['model_package_id']) if change_request else None
    runtime_input_source = 'change_request_override' if change_request and change_request.get('override_input_data_storage_path') else 'base'
    runtime_input_path = (
        change_request.get('override_input_data_storage_path')
        if runtime_input_source == 'change_request_override' and change_request
        else model_package.get('input_data_storage_path') if model_package else None
    )
    runtime_input_filename = (
        change_request.get('override_input_data_filename')
        if runtime_input_source == 'change_request_override' and change_request
        else model_package.get('input_data_filename') if model_package else None
    )
    model_preset, model_provider, model_name, api_key_provider = infer_run_selection(run)
    artifacts = queries.list_run_artifacts(run['id']) if include_details else []
    for artifact in artifacts:
        if artifact.get('storage_path'):
            artifact['signed_url'] = storage.create_signed_url(bucket=settings.artifacts_bucket, path=artifact['storage_path'])
    payload = {
        **run,
        'project_id': change_request.get('project_id') if change_request else None,
        'model_package_id': change_request.get('model_package_id') if change_request else None,
        'model_package_filename': model_package.get('filename') if model_package else None,
        'change_request_summary': change_request.get('what_should_change') if change_request else None,
        'runtime_input_source': runtime_input_source,
        'runtime_input_filename': runtime_input_filename,
        'runtime_input_file_url': (
            storage.create_signed_url(bucket=settings.models_bucket, path=runtime_input_path)
            if runtime_input_path
            else None
        ),
        'model_preset': model_preset,
        'model_provider': model_provider,
        'model_name': model_name,
        'api_key_provider': api_key_provider,
        'credential_source': 'user_saved',
        'clarification_questions': run.get('clarification_questions') or [],
        'clarification_answers': run.get('clarification_answers') or [],
        'events': queries.list_run_events(run['id']) if include_details else [],
        'artifacts': artifacts,
    }
    return payload
