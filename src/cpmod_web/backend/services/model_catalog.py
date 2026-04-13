from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

LLMProvider = Literal['openai', 'openrouter']
ModelPreset = Literal['fast', 'quality']
ReasoningEffort = Literal['none', 'minimal', 'low', 'medium', 'high']


@dataclass(frozen=True)
class ModelCatalogEntry:
    preset: ModelPreset
    provider: LLMProvider
    model: str
    label: str
    description: str
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int | None = None
    is_default: bool = False

    @property
    def id(self) -> str:
        return f'{self.preset}:{self.provider}:{self.model}'

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['id'] = self.id
        payload['model_name'] = payload.pop('model')
        return payload


MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        preset='fast',
        provider='openai',
        model='gpt-5.4-mini',
        label='GPT-5.4 Mini',
        description='Lower-latency OpenAI model for cheaper exploratory runs.',
        reasoning_effort='none',
        is_default=True,
    ),
    ModelCatalogEntry(
        preset='fast',
        provider='openrouter',
        model='openai/gpt-5.4-mini',
        label='GPT-5.4 Mini via OpenRouter',
        description='Fast OpenRouter route for teams standardizing on a shared provider gateway.',
        reasoning_effort='none',
    ),
    ModelCatalogEntry(
        preset='quality',
        provider='openai',
        model='gpt-5.4',
        label='GPT-5.4',
        description='Higher-quality OpenAI model for final modification attempts.',
        reasoning_effort='high',
        is_default=True,
    ),
    ModelCatalogEntry(
        preset='quality',
        provider='openrouter',
        model='anthropic/claude-opus-4.6',
        label='Claude Opus 4.6 via OpenRouter',
        description='High-capability OpenRouter option for deeper reasoning and plan validation.',
        reasoning_effort='high',
    ),
)


def list_model_catalog() -> list[ModelCatalogEntry]:
    return list(MODEL_CATALOG)


def list_model_catalog_payload() -> list[dict[str, object]]:
    return [entry.to_dict() for entry in MODEL_CATALOG]


def list_supported_providers() -> list[LLMProvider]:
    seen: list[LLMProvider] = []
    for entry in MODEL_CATALOG:
        if entry.provider not in seen:
            seen.append(entry.provider)
    return seen


def get_catalog_entry(*, preset: ModelPreset, provider: LLMProvider, model_name: str) -> ModelCatalogEntry | None:
    for entry in MODEL_CATALOG:
        if entry.preset == preset and entry.provider == provider and entry.model == model_name:
            return entry
    return None


def get_default_catalog_entry(preset: ModelPreset) -> ModelCatalogEntry:
    for entry in MODEL_CATALOG:
        if entry.preset == preset and entry.is_default:
            return entry
    for entry in MODEL_CATALOG:
        if entry.preset == preset:
            return entry
    raise ValueError(f'No catalog entries configured for preset {preset!r}.')


def infer_run_selection(run: dict[str, object]) -> tuple[ModelPreset, LLMProvider, str, LLMProvider]:
    preset = str(run.get('model_preset') or run.get('model_config') or 'quality')
    normalized_preset: ModelPreset = 'fast' if preset == 'fast' else 'quality'
    provider = run.get('model_provider')
    model_name = run.get('model_name')
    api_key_provider = run.get('api_key_provider')
    if isinstance(provider, str) and isinstance(model_name, str):
        resolved_provider: LLMProvider = 'openrouter' if provider == 'openrouter' else 'openai'
        resolved_key_provider: LLMProvider = 'openrouter' if api_key_provider == 'openrouter' else resolved_provider
        return normalized_preset, resolved_provider, model_name, resolved_key_provider
    entry = get_default_catalog_entry(normalized_preset)
    return normalized_preset, entry.provider, entry.model, entry.provider
