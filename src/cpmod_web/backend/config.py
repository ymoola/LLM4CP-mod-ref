from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent / '.env'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_prefix='CPMOD_WEB_',
        extra='ignore',
    )

    app_env: Literal['development', 'production'] = 'development'
    backend_base_url: str = 'http://localhost:8000'
    frontend_base_url: str = 'http://localhost:3000'

    supabase_url: str = ''
    supabase_service_role_key: str = ''
    supabase_publishable_key: str = ''
    credential_encryption_secret: str = ''

    models_bucket: str = 'models'
    artifacts_bucket: str = 'artifacts'

    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_site_url: str | None = None
    openrouter_site_name: str = 'CP Mod Web'

    e2b_api_key: str | None = None
    e2b_template: str | None = None
    execution_backend: Literal['auto', 'local', 'e2b'] = 'auto'

    max_planner_validation_loops: int = 5
    max_execution_loops: int = 5
    max_validator_loops: int = 5
    execution_timeout_seconds: int = 30

    local_executor_workdir: str = '.cpmod_web_runtime'
    log_level: str = 'INFO'

    @property
    def resolved_execution_backend(self) -> Literal['local', 'e2b']:
        if self.execution_backend == 'auto':
            return 'e2b' if self.app_env == 'production' else 'local'
        return self.execution_backend

    def readiness_issues(self) -> list[str]:
        issues: list[str] = []
        if not self.supabase_url:
            issues.append('CPMOD_WEB_SUPABASE_URL is not configured.')
        if not self.supabase_service_role_key:
            issues.append('CPMOD_WEB_SUPABASE_SERVICE_ROLE_KEY is not configured.')
        if not self.credential_encryption_secret:
            issues.append('CPMOD_WEB_CREDENTIAL_ENCRYPTION_SECRET is not configured.')
        if self.resolved_execution_backend == 'e2b' and not self.e2b_api_key:
            issues.append('CPMOD_WEB_E2B_API_KEY is required when the execution backend resolves to E2B.')
        return issues

    def validate_for_runtime(self) -> None:
        issues = self.readiness_issues()
        if self.app_env == 'production' and issues:
            raise RuntimeError('Invalid production configuration: ' + ' '.join(issues))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
