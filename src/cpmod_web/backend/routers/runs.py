from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import get_settings
from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ClarificationSubmit, RunArtifactRead, RunCreate, RunRead
from ..models.domain import RunStatus
from ..services.storage_service import StorageService

router = APIRouter(prefix='/runs', tags=['runs'])


def _serialize_run(run: dict, *, include_details: bool = True) -> dict:
    storage = StorageService()
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
    artifacts = queries.list_run_artifacts(run['id']) if include_details else []
    for artifact in artifacts:
        if artifact.get('storage_path'):
            artifact['signed_url'] = storage.create_signed_url(bucket=get_settings().artifacts_bucket, path=artifact['storage_path'])
    return {
        **run,
        'model_package_id': change_request.get('model_package_id') if change_request else None,
        'model_package_filename': model_package.get('filename') if model_package else None,
        'change_request_summary': change_request.get('what_should_change') if change_request else None,
        'runtime_input_source': runtime_input_source,
        'runtime_input_filename': runtime_input_filename,
        'runtime_input_file_url': (
            storage.create_signed_url(bucket=get_settings().models_bucket, path=runtime_input_path)
            if runtime_input_path
            else None
        ),
        'clarification_questions': run.get('clarification_questions') or [],
        'clarification_answers': run.get('clarification_answers') or [],
        'events': queries.list_run_events(run['id']) if include_details else [],
        'artifacts': artifacts,
    }


@router.post('', response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, current_user: AuthenticatedUser = Depends(get_current_user)):
    change_request = queries.get_change_request(payload.change_request_id)
    if not change_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    run = queries.create_workflow_run(
        {
            'change_request_id': payload.change_request_id,
            'status': RunStatus.PENDING.value,
            'model_config': payload.model_preset,
            'clarification_questions': [],
            'clarification_answers': [],
        }
    )
    return _serialize_run(run)


@router.get('/{run_id}', response_model=RunRead)
def get_run(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    run = queries.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    change_request = queries.get_change_request(run['change_request_id'])
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    return _serialize_run(run)


@router.get('/{run_id}/artifacts', response_model=list[RunArtifactRead])
def get_run_artifacts(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    run = queries.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    change_request = queries.get_change_request(run['change_request_id'])
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    return _serialize_run(run)['artifacts']


@router.post('/{run_id}/clarify', response_model=RunRead)
def submit_clarification(run_id: str, payload: ClarificationSubmit, current_user: AuthenticatedUser = Depends(get_current_user)):
    run = queries.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    change_request = queries.get_change_request(run['change_request_id'])
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    if run['status'] != RunStatus.AWAITING_CLARIFICATION.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Run is not awaiting clarification.')
    updated = queries.update_workflow_run(
        run_id,
        {
            'status': RunStatus.PENDING.value,
            'clarification_answers': payload.answers,
        },
    )
    return _serialize_run(updated)
