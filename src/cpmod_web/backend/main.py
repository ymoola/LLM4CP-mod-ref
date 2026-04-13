from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import change_requests, dashboard, model_packages, projects, runs, settings as settings_router

settings = get_settings()
settings.validate_for_runtime()
logger = logging.getLogger(__name__)

app = FastAPI(title='CP Mod Web API', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url, 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(projects.router)
app.include_router(model_packages.router)
app.include_router(change_requests.router)
app.include_router(runs.router)
app.include_router(dashboard.router)
app.include_router(settings_router.router)


@app.on_event('startup')
def log_readiness_issues() -> None:
    issues = settings.readiness_issues()
    if issues:
        logger.warning('CP Mod Web backend readiness issues: %s', ' | '.join(issues))


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/ready')
def ready():
    issues = settings.readiness_issues()
    payload = {
        'status': 'ready' if not issues else 'not_ready',
        'app_env': settings.app_env,
        'execution_backend': settings.resolved_execution_backend,
        'issues': issues,
    }
    if issues:
        return JSONResponse(status_code=503, content=payload)
    return payload
