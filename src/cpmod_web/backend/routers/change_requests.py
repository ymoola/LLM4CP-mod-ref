from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from ..config import get_settings
from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ChangeRequestRead
from ..services.resource_service import delete_change_request_with_artifacts
from ..services.storage_service import StorageService

router = APIRouter(tags=['change-requests'])


def _serialize_change_request(change_request: dict):
    storage = StorageService()
    settings = get_settings()
    model_package = queries.get_model_package(change_request['model_package_id'])
    return {
        **change_request,
        'model_package_filename': model_package.get('filename') if model_package else None,
        'override_input_data_file_url': (
            storage.create_signed_url(bucket=settings.models_bucket, path=change_request['override_input_data_storage_path'])
            if change_request.get('override_input_data_storage_path')
            else None
        ),
    }


@router.get('/projects/{project_id}/change-requests', response_model=list[ChangeRequestRead])
def list_change_requests(project_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    project = queries.get_project(project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found.')
    return [_serialize_change_request(change_request) for change_request in queries.list_change_requests(project_id=project_id)]


@router.get('/change-requests/{change_request_id}', response_model=ChangeRequestRead)
def get_change_request(change_request_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    change_request = queries.get_change_request(change_request_id)
    if not change_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    return _serialize_change_request(change_request)


@router.post('/projects/{project_id}/change-requests', response_model=ChangeRequestRead, status_code=status.HTTP_201_CREATED)
async def create_change_request(
    project_id: str,
    model_package_id: str = Form(...),
    what_should_change: str = Form(...),
    what_must_stay_the_same: str | None = Form(default=None),
    additional_detail: str | None = Form(default=None),
    override_input_data_file: UploadFile | None = File(default=None),
    override_input_value_info: str | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    project = queries.get_project(project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found.')
    package = queries.get_model_package(model_package_id)
    if not package or package['project_id'] != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Model package not found for project.')
    if package.get('validation_status') != 'validated':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Model package must pass upload validation before creating a change request.')

    override_filename: str | None = None
    override_storage_path: str | None = None
    if override_input_data_file:
        if not override_input_data_file.filename or not override_input_data_file.filename.endswith('.json'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Override input data must be a .json file.')
        try:
            override_payload = json.loads((await override_input_data_file.read()).decode('utf-8'))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'override input_data.json is not valid JSON: {exc}') from exc
        storage = StorageService()
        override_filename = override_input_data_file.filename
        override_storage_path = storage.upload_json(
            bucket=get_settings().models_bucket,
            path=f'projects/{project_id}/change-requests/{uuid4()}/{override_filename}',
            payload=override_payload,
        )

    change_request_id = str(uuid4())
    change_request = queries.create_change_request(
        {
            'id': change_request_id,
            'project_id': project_id,
            'model_package_id': model_package_id,
            'what_should_change': what_should_change.strip(),
            'what_must_stay_the_same': (what_must_stay_the_same or '').strip(),
            'objective_change': 'unsure',
            'expected_output_changes': None,
            'additional_detail': (additional_detail or '').strip() or None,
            'override_input_data_filename': override_filename,
            'override_input_data_storage_path': override_storage_path,
            'override_input_value_info': (override_input_value_info or '').strip() or None,
            'status': 'submitted',
        }
    )
    return _serialize_change_request(change_request)


@router.delete('/change-requests/{change_request_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_change_request(change_request_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    change_request = queries.get_change_request(change_request_id)
    if not change_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    project = queries.get_project(project_id=change_request['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Change request not found.')
    delete_change_request_with_artifacts(change_request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
