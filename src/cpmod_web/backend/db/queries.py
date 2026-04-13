from __future__ import annotations

from typing import Any

from .supabase_client import get_supabase_admin


def _table(name: str):
    return get_supabase_admin().table(name)


def create_project(*, user_id: str, name: str, description: str | None) -> dict[str, Any]:
    payload = {'user_id': user_id, 'name': name, 'description': description}
    return _table('projects').insert(payload).execute().data[0]


def list_projects(*, user_id: str) -> list[dict[str, Any]]:
    return _table('projects').select('*').eq('user_id', user_id).order('created_at', desc=True).execute().data or []


def get_project(*, project_id: str, user_id: str) -> dict[str, Any] | None:
    data = _table('projects').select('*').eq('id', project_id).eq('user_id', user_id).limit(1).execute().data or []
    return data[0] if data else None


def get_project_admin(project_id: str) -> dict[str, Any] | None:
    data = _table('projects').select('*').eq('id', project_id).limit(1).execute().data or []
    return data[0] if data else None


def create_model_package(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('model_packages').insert(payload).execute().data[0]


def update_model_package(model_package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _table('model_packages').update(payload).eq('id', model_package_id).execute().data[0]


def list_model_packages(*, project_id: str) -> list[dict[str, Any]]:
    return _table('model_packages').select('*').eq('project_id', project_id).order('created_at', desc=True).execute().data or []


def list_model_packages_for_user(*, user_id: str) -> list[dict[str, Any]]:
    project_ids = [project['id'] for project in list_projects(user_id=user_id)]
    if not project_ids:
        return []
    return _table('model_packages').select('*').in_('project_id', project_ids).order('created_at', desc=True).execute().data or []


def get_model_package(model_package_id: str) -> dict[str, Any] | None:
    data = _table('model_packages').select('*').eq('id', model_package_id).limit(1).execute().data or []
    return data[0] if data else None


def delete_model_package(model_package_id: str) -> None:
    _table('model_packages').delete().eq('id', model_package_id).execute()


def create_change_request(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('change_requests').insert(payload).execute().data[0]


def list_change_requests(*, project_id: str) -> list[dict[str, Any]]:
    return _table('change_requests').select('*').eq('project_id', project_id).order('created_at', desc=True).execute().data or []


def list_change_requests_for_user(*, user_id: str) -> list[dict[str, Any]]:
    project_ids = [project['id'] for project in list_projects(user_id=user_id)]
    if not project_ids:
        return []
    return _table('change_requests').select('*').in_('project_id', project_ids).order('created_at', desc=True).execute().data or []


def get_change_request(change_request_id: str) -> dict[str, Any] | None:
    data = _table('change_requests').select('*').eq('id', change_request_id).limit(1).execute().data or []
    return data[0] if data else None


def delete_change_request(change_request_id: str) -> None:
    _table('change_requests').delete().eq('id', change_request_id).execute()


def create_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('workflow_runs').insert(payload).execute().data[0]


def update_workflow_run(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _table('workflow_runs').update(payload).eq('id', run_id).execute().data[0]


def get_workflow_run(run_id: str) -> dict[str, Any] | None:
    data = _table('workflow_runs').select('*').eq('id', run_id).limit(1).execute().data or []
    return data[0] if data else None


def list_workflow_runs_for_project(project_id: str) -> list[dict[str, Any]]:
    change_request_ids = [
        change_request['id']
        for change_request in list_change_requests(project_id=project_id)
    ]
    if not change_request_ids:
        return []
    return (
        _table('workflow_runs')
        .select('*')
        .in_('change_request_id', change_request_ids)
        .order('created_at', desc=True)
        .execute()
        .data
        or []
    )


def list_workflow_runs_for_user(*, user_id: str) -> list[dict[str, Any]]:
    change_request_ids = [change_request['id'] for change_request in list_change_requests_for_user(user_id=user_id)]
    if not change_request_ids:
        return []
    return _table('workflow_runs').select('*').in_('change_request_id', change_request_ids).order('created_at', desc=True).execute().data or []


def list_workflow_runs_for_change_request(change_request_id: str) -> list[dict[str, Any]]:
    return (
        _table('workflow_runs')
        .select('*')
        .eq('change_request_id', change_request_id)
        .order('created_at', desc=True)
        .execute()
        .data
        or []
    )


def list_run_events(run_id: str) -> list[dict[str, Any]]:
    return _table('run_events').select('*').eq('run_id', run_id).order('created_at').execute().data or []


def add_run_event(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('run_events').insert(payload).execute().data[0]


def list_run_artifacts(run_id: str) -> list[dict[str, Any]]:
    return _table('run_artifacts').select('*').eq('run_id', run_id).order('created_at').execute().data or []


def add_run_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('run_artifacts').insert(payload).execute().data[0]


def list_user_api_credentials(*, user_id: str) -> list[dict[str, Any]]:
    return _table('user_api_credentials').select('*').eq('user_id', user_id).order('updated_at', desc=True).execute().data or []


def get_user_api_credential(*, user_id: str, provider: str) -> dict[str, Any] | None:
    data = _table('user_api_credentials').select('*').eq('user_id', user_id).eq('provider', provider).limit(1).execute().data or []
    return data[0] if data else None


def upsert_user_api_credential(payload: dict[str, Any]) -> dict[str, Any]:
    return _table('user_api_credentials').upsert(payload, on_conflict='user_id,provider').execute().data[0]


def delete_user_api_credential(*, user_id: str, provider: str) -> None:
    _table('user_api_credentials').delete().eq('user_id', user_id).eq('provider', provider).execute()


def list_run_artifacts_for_model_package(model_package_id: str) -> list[dict[str, Any]]:
    return (
        _table('run_artifacts')
        .select('*')
        .eq('type', 'base_validation_log')
        .eq('model_package_id', model_package_id)
        .order('created_at', desc=True)
        .execute()
        .data
        or []
    )


def claim_pending_run() -> dict[str, Any] | None:
    response = get_supabase_admin().rpc('claim_pending_run').execute()
    data = response.data or []
    return data[0] if data else None
