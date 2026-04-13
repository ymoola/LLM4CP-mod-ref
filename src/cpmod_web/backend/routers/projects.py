from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ProjectCreate, ProjectRead, RunSummaryRead
from ..services.run_serialization import serialize_run

router = APIRouter(prefix='/projects', tags=['projects'])


@router.get('', response_model=list[ProjectRead])
def list_projects(current_user: AuthenticatedUser = Depends(get_current_user)):
    return queries.list_projects(user_id=current_user.id)


@router.post('', response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, current_user: AuthenticatedUser = Depends(get_current_user)):
    return queries.create_project(user_id=current_user.id, name=payload.name, description=payload.description)


@router.get('/{project_id}/runs', response_model=list[RunSummaryRead])
def list_project_runs(project_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    project = queries.get_project(project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found.')
    return [serialize_run(run, include_details=False) for run in queries.list_workflow_runs_for_project(project_id)]
