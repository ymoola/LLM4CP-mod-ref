from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from ..config import get_settings

LLMProvider = Literal['openai', 'openrouter']
ReasoningEffort = Literal['none', 'minimal', 'low', 'medium', 'high']


@dataclass(frozen=True)
class ProductLLMConfig:
    provider: LLMProvider
    model: str
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int | None = None


def get_model_config(preset: Literal['fast', 'quality']) -> ProductLLMConfig:
    settings = get_settings()
    if preset == 'fast':
        return ProductLLMConfig(
            provider=settings.fast_provider,
            model=settings.fast_model,
            reasoning_effort=settings.fast_reasoning_effort,
        )
    return ProductLLMConfig(
        provider=settings.quality_provider,
        model=settings.quality_model,
        reasoning_effort=settings.quality_reasoning_effort,
    )


class LLMService:
    def __init__(self, config: ProductLLMConfig):
        self.config = config
        settings = get_settings()
        kwargs: dict[str, Any] = {}
        if config.provider == 'openrouter':
            kwargs['api_key'] = settings.openrouter_api_key
            kwargs['base_url'] = settings.openrouter_base_url
            headers = {}
            if settings.openrouter_site_url:
                headers['HTTP-Referer'] = settings.openrouter_site_url
            if settings.openrouter_site_name:
                headers['X-OpenRouter-Title'] = settings.openrouter_site_name
            if headers:
                kwargs['default_headers'] = headers
        else:
            kwargs['api_key'] = settings.openai_api_key
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
