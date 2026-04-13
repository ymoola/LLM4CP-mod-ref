from __future__ import annotations

from fastapi import APIRouter, Depends

from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import DashboardOverviewRead
from ..services.run_serialization import serialize_run

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


def _recent(items: list[dict], limit: int = 5) -> list[dict]:
    return items[:limit]


@router.get('/overview', response_model=DashboardOverviewRead)
def get_dashboard_overview(current_user: AuthenticatedUser = Depends(get_current_user)):
    projects = queries.list_projects(user_id=current_user.id)
    model_packages = queries.list_model_packages_for_user(user_id=current_user.id)
    runs = [serialize_run(run, include_details=False) for run in queries.list_workflow_runs_for_user(user_id=current_user.id)]

    awaiting_clarification = [run for run in runs if run.get('status') == 'awaiting_clarification']
    needs_review = [run for run in runs if run.get('status') == 'needs_review']

    return {
        'counts': {
            'total_projects': len(projects),
            'validated_model_packages': sum(1 for package in model_packages if package.get('validation_status') == 'validated'),
            'completed_runs': sum(1 for run in runs if run.get('status') == 'completed'),
            'runs_needing_review': len(needs_review),
            'failed_runs': sum(1 for run in runs if run.get('status') == 'failed'),
        },
        'recent_projects': _recent(projects),
        'recent_runs': _recent(runs),
        'runs_awaiting_clarification': _recent(awaiting_clarification),
        'runs_needing_review': _recent(needs_review),
    }
