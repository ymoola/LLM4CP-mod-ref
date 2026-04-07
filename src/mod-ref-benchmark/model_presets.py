from __future__ import annotations

from typing import Any

from llm_client import DEFAULT_OPENAI_REASONING_EFFORT


MODEL_PRESETS: list[dict[str, Any]] = [
    {
        "key": "openai_gpt_5_4",
        "label": "OpenAI GPT-5.4",
        "provider": "openai",
        "model": "gpt-5.4",
        "reasoning_effort": DEFAULT_OPENAI_REASONING_EFFORT,
        "docs_url": "https://platform.openai.com/docs/models/compare",
        "pricing_source_url": "https://developers.openai.com/api/docs/models/gpt-5.4-pro",
        "pricing_per_million": {
            "prompt": 2.50,
            "completion": 15.00,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_gpt_5_4_mini",
        "label": "OpenRouter GPT-5.4 mini",
        "provider": "openrouter",
        "model": "openai/gpt-5.4-mini",
        "reasoning_effort": "none",
        "docs_url": "https://platform.openai.com/docs/models/compare",
        "pricing_source_url": "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        "pricing_per_million": {
            "prompt": 0.75,
            "completion": 4.50,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_qwen3_next_80b_a3b_instruct",
        "label": "OpenRouter Qwen3-Next 80B A3B Instruct",
        "provider": "openrouter",
        "model": "qwen/qwen3-next-80b-a3b-instruct",
        "reasoning_effort": None,
        "docs_url": "https://openrouter.ai/qwen/qwen3-next-80b-a3b-instruct/providers",
        "pricing_source_url": "https://openrouter.ai/qwen/qwen3-next-80b-a3b-instruct",
        "pricing_per_million": {
            "prompt": 0.09,
            "completion": 1.10,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_qwen3_5_27b_reasoning_off",
        "label": "OpenRouter Qwen3.5 27B (reasoning off)",
        "provider": "openrouter",
        "model": "qwen/qwen3.5-27b",
        "reasoning_effort": "none",
        "docs_url": "https://openrouter.ai/compare/qwen/qwen3.5-27b/z-ai/glm-4.7-flash",
        "pricing_source_url": "https://openrouter.ai/qwen/qwen3.5-27b",
        "pricing_per_million": {
            "prompt": 0.195,
            "completion": 1.56,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_gemini_3_1_flash_lite_preview",
        "label": "OpenRouter Gemini 3.1 Flash Lite Preview",
        "provider": "openrouter",
        "model": "google/gemini-3.1-flash-lite-preview",
        "reasoning_effort": None,
        "docs_url": "https://openrouter.ai/google/gemini-3.1-flash-lite-preview",
        "pricing_source_url": "https://openrouter.ai/google/gemini-3.1-flash-lite-preview",
        "pricing_per_million": {
            "prompt": 0.25,
            "completion": 1.50,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_claude_opus_4_6_high_reasoning",
        "label": "OpenRouter Claude Opus 4.6 (high reasoning)",
        "provider": "openrouter",
        "model": "anthropic/claude-opus-4.6",
        "reasoning_effort": "high",
        "docs_url": "https://openrouter.ai/anthropic/claude-opus-4.6/api",
        "pricing_source_url": "https://openrouter.ai/anthropic/claude-opus-4.6",
        "pricing_per_million": {
            "prompt": 5.0,
            "completion": 25.0,
            "request": 0.0,
        },
    },
    {
        "key": "openrouter_qwen3_5_9b_reasoning_off",
        "label": "OpenRouter Qwen3.5 9B (reasoning off)",
        "provider": "openrouter",
        "model": "qwen/qwen3.5-9b",
        "reasoning_effort": "none",
        "docs_url": "https://openrouter.ai/compare/black-forest-labs/flux.2-max/qwen/qwen3.5-9b",
        "pricing_source_url": "https://openrouter.ai/qwen/qwen3.5-9b",
        "pricing_per_million": {
            "prompt": 0.05,
            "completion": 0.15,
            "request": 0.0,
        },
    },
]


def select_model_presets(only_keys: list[str] | None = None) -> list[dict[str, Any]]:
    if not only_keys:
        return list(MODEL_PRESETS)
    requested = set(only_keys)
    selected = [preset for preset in MODEL_PRESETS if preset["key"] in requested]
    missing = sorted(requested - {preset["key"] for preset in selected})
    if missing:
        raise ValueError(f"Unknown model preset keys: {missing}")
    return selected


def get_model_preset_by_key(key: str) -> dict[str, Any] | None:
    for preset in MODEL_PRESETS:
        if preset["key"] == key:
            return dict(preset)
    return None
