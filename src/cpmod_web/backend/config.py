from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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

    models_bucket: str = 'models'
    artifacts_bucket: str = 'artifacts'

    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_site_url: str | None = None
    openrouter_site_name: str = 'CP Mod Web'

    e2b_api_key: str | None = None
    e2b_template: str | None = None
    execution_backend: Literal['auto', 'local', 'e2b'] = 'auto'

    fast_provider: Literal['openai', 'openrouter'] = 'openai'
    fast_model: str = 'gpt-5.4-mini'
    fast_reasoning_effort: Literal['none', 'minimal', 'low', 'medium', 'high'] | None = 'none'

    quality_provider: Literal['openai', 'openrouter'] = 'openrouter'
    quality_model: str = 'anthropic/claude-opus-4.6'
    quality_reasoning_effort: Literal['none', 'minimal', 'low', 'medium', 'high'] | None = 'high'

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
