from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from ..config import get_settings
from .model_catalog import LLMProvider, ModelPreset, ReasoningEffort, get_catalog_entry


@dataclass(frozen=True)
class ProductLLMConfig:
    provider: LLMProvider
    model: str
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int | None = None


def get_model_config(*, preset: ModelPreset, provider: LLMProvider, model_name: str) -> ProductLLMConfig:
    entry = get_catalog_entry(preset=preset, provider=provider, model_name=model_name)
    if not entry:
        raise ValueError(f'Unsupported model selection: preset={preset!r}, provider={provider!r}, model={model_name!r}')
    return ProductLLMConfig(
        provider=entry.provider,
        model=entry.model,
        reasoning_effort=entry.reasoning_effort,
        max_output_tokens=entry.max_output_tokens,
    )


class LLMService:
    def __init__(self, config: ProductLLMConfig, *, api_key: str):
        self.config = config
        if not api_key:
            raise ValueError('A provider API key is required to initialize the LLM service.')
        settings = get_settings()
        kwargs: dict[str, Any] = {}
        if config.provider == 'openrouter':
            kwargs['api_key'] = api_key
            kwargs['base_url'] = settings.openrouter_base_url
            headers = {}
            if settings.openrouter_site_url:
                headers['HTTP-Referer'] = settings.openrouter_site_url
            if settings.openrouter_site_name:
                headers['X-OpenRouter-Title'] = settings.openrouter_site_name
            if headers:
                kwargs['default_headers'] = headers
        else:
            kwargs['api_key'] = api_key
        self.client = OpenAI(**kwargs)

    def _apply_reasoning(self, params: dict[str, Any]) -> None:
        if self.config.reasoning_effort and self.config.reasoning_effort != 'none':
            params['reasoning'] = {'effort': self.config.reasoning_effort}

    def generate_text(self, *, prompt: str, system: str | None = None) -> str:
        params: dict[str, Any] = {'model': self.config.model, 'input': prompt}
        if system:
            params['instructions'] = system
        self._apply_reasoning(params)
        if self.config.max_output_tokens is not None:
            params['max_output_tokens'] = self.config.max_output_tokens
        response = self.client.responses.create(**params)
        return getattr(response, 'output_text', '') or ''

    def generate_json(self, *, prompt: str, schema: dict[str, Any], schema_name: str, system: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            'model': self.config.model,
            'input': prompt,
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': schema_name,
                    'strict': True,
                    'schema': schema,
                }
            },
        }
        if system:
            params['instructions'] = system
        self._apply_reasoning(params)
        if self.config.max_output_tokens is not None:
            params['max_output_tokens'] = self.config.max_output_tokens
        response = self.client.responses.create(**params)
        raw = getattr(response, 'output_text', '') or ''
        return json.loads(raw)
