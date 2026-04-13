from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ClarificationSubmit, RunArtifactRead, RunCreate, RunRead
from ..models.domain import RunStatus
from ..services.credential_service import CredentialError, supported_provider
from ..services.model_catalog import get_catalog_entry
from ..services.run_serialization import serialize_run

router = APIRouter(prefix='/runs', tags=['runs'])


@router.post('', response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, current_user: AuthenticatedUser = Depends(get_current_user)):
    change_request = queries.get_change_request(payload.change_request_id)
    if not change_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    try:
        normalized_key_provider = supported_provider(payload.api_key_provider)
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if normalized_key_provider != payload.model_provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The selected API key provider must match the selected model provider.')
    if not get_catalog_entry(preset=payload.model_preset, provider=payload.model_provider, model_name=payload.model_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Selected model is not available for that preset.')
    if not queries.get_user_api_credential(user_id=current_user.id, provider=normalized_key_provider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Save an API key for {normalized_key_provider} before creating this run.')
    run = queries.create_workflow_run(
        {
            'change_request_id': payload.change_request_id,
            'status': RunStatus.PENDING.value,
            'model_config': payload.model_preset,
            'model_preset': payload.model_preset,
            'model_provider': payload.model_provider,
            'model_name': payload.model_name,
            'api_key_provider': normalized_key_provider,
            'clarification_questions': [],
            'clarification_answers': [],
        }
    )
    return serialize_run(run)


@router.get('/{run_id}', response_model=RunRead)
def get_run(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    run = queries.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    change_request = queries.get_change_request(run['change_request_id'])
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    return serialize_run(run)


@router.get('/{run_id}/artifacts', response_model=list[RunArtifactRead])
def get_run_artifacts(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    run = queries.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    change_request = queries.get_change_request(run['change_request_id'])
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')
    return serialize_run(run)['artifacts']


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
    return serialize_run(updated)
