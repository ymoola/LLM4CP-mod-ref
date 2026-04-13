from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import change_requests, model_packages, projects, runs

settings = get_settings()

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


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}
