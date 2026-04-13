from __future__ import annotations

from ..config import get_settings
from ..db import queries
from .storage_service import StorageService


def collect_change_request_artifact_paths(change_request_id: str) -> tuple[list[str], list[str]]:
    run_paths: list[str] = []
    run_ids: list[str] = []
    for run in queries.list_workflow_runs_for_change_request(change_request_id):
        run_ids.append(run['id'])
        for artifact in queries.list_run_artifacts(run['id']):
            storage_path = artifact.get('storage_path')
            if storage_path:
                run_paths.append(storage_path)
    return run_ids, run_paths


def delete_change_request_with_artifacts(change_request_id: str) -> None:
    settings = get_settings()
    storage = StorageService()
    change_request = queries.get_change_request(change_request_id)
    _, artifact_paths = collect_change_request_artifact_paths(change_request_id)
    if change_request and change_request.get('override_input_data_storage_path'):
        storage.delete_paths(bucket=settings.models_bucket, paths=[change_request['override_input_data_storage_path']])
    storage.delete_paths(bucket=settings.artifacts_bucket, paths=artifact_paths)
    queries.delete_change_request(change_request_id)


def delete_model_package_with_artifacts(model_package_id: str) -> None:
    settings = get_settings()
    storage = StorageService()
    package = queries.get_model_package(model_package_id)
    if not package:
        return

    model_paths = [
        package.get('model_storage_path'),
        package.get('problem_description_storage_path'),
        package.get('input_data_storage_path'),
    ]
    validation_artifact_paths = [
        artifact.get('storage_path')
        for artifact in queries.list_run_artifacts_for_model_package(model_package_id)
        if artifact.get('storage_path')
    ]

    descendant_artifact_paths: list[str] = []
    for change_request in queries.list_change_requests(project_id=package['project_id']):
        if change_request['model_package_id'] != model_package_id:
            continue
        if change_request.get('override_input_data_storage_path'):
            model_paths.append(change_request['override_input_data_storage_path'])
        _, artifact_paths = collect_change_request_artifact_paths(change_request['id'])
        descendant_artifact_paths.extend(artifact_paths)

    storage.delete_paths(bucket=settings.models_bucket, paths=model_paths)
    storage.delete_paths(
        bucket=settings.artifacts_bucket,
        paths=validation_artifact_paths + descendant_artifact_paths,
    )
    queries.delete_model_package(model_package_id)
