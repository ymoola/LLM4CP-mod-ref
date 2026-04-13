from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from ..config import get_settings
from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ModelPackageRead
from ..services.model_package_service import create_model_package_with_validation
from ..services.resource_service import delete_model_package_with_artifacts
from ..services.storage_service import StorageService

router = APIRouter(tags=['model-packages'])


def _serialize_model_package(package: dict) -> dict:
    storage = StorageService()
    settings = get_settings()
    validation_artifacts = queries.list_run_artifacts_for_model_package(package['id'])
    latest_validation_log = validation_artifacts[0] if validation_artifacts else None
    return {
        **package,
        'model_file_url': storage.create_signed_url(bucket=settings.models_bucket, path=package['model_storage_path']),
        'problem_description_file_url': storage.create_signed_url(bucket=settings.models_bucket, path=package['problem_description_storage_path']),
        'input_data_file_url': storage.create_signed_url(bucket=settings.models_bucket, path=package['input_data_storage_path']),
        'validation_log_url': (
            storage.create_signed_url(bucket=settings.artifacts_bucket, path=latest_validation_log['storage_path'])
            if latest_validation_log and latest_validation_log.get('storage_path')
            else None
        ),
    }


@router.get('/projects/{project_id}/model-packages', response_model=list[ModelPackageRead])
def list_model_packages(project_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    project = queries.get_project(project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found.')
    return [_serialize_model_package(package) for package in queries.list_model_packages(project_id=project_id)]


@router.get('/model-packages/{model_package_id}', response_model=ModelPackageRead)
def get_model_package(model_package_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    package = queries.get_model_package(model_package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Model package not found.')
    project = queries.get_project(project_id=package['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Model package not found.')
    return _serialize_model_package(package)


@router.post('/projects/{project_id}/model-packages', response_model=ModelPackageRead, status_code=status.HTTP_201_CREATED)
async def upload_model_package(
    project_id: str,
    model_file: UploadFile = File(...),
    description_file: UploadFile = File(...),
    input_data_file: UploadFile = File(...),
    execution_mode: str = Form(default='script'),
    entrypoint_name: str | None = Form(default=None),
    output_variable_names: str | None = Form(default=None),
    key_names_to_preserve: str | None = Form(default=None),
    input_value_info: str | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    project = queries.get_project(project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found.')
    package = await create_model_package_with_validation(
        project_id=project_id,
        model_file=model_file,
        description_file=description_file,
        input_data_file=input_data_file,
        execution_mode=execution_mode,
        entrypoint_name=entrypoint_name,
        output_variable_names=output_variable_names,
        key_names_to_preserve=key_names_to_preserve,
        input_value_info=input_value_info,
    )
    return _serialize_model_package(package)


@router.delete('/model-packages/{model_package_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_model_package(model_package_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    package = queries.get_model_package(model_package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Model package not found.')
    project = queries.get_project(project_id=package['project_id'], user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Model package not found.')
    delete_model_package_with_artifacts(model_package_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
