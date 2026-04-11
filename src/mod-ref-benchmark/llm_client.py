from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional


LLMProvider = Literal["ollama", "openai", "openrouter"]
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high"]
DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-5.4"
DEFAULT_OPENAI_REASONING_EFFORT: Literal["high"] = "high"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
JSON_RETRY_INSTRUCTION = (
    "\n\nIMPORTANT RETRY: Your previous reply was malformed JSON. "
    "Return only valid JSON that matches the requested schema. "
    "Do not include markdown fences, comments, or extra text."
)
CLAUDE_46_MODELS = {"anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6"}
VERBOSITY_BY_REASONING_EFFORT = {
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
}


def _maybe_load_dotenv() -> None:
    try:
        from dotenv import find_dotenv, load_dotenv

        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path)
    except Exception:
        # Don't fail if python-dotenv isn't available; downstream SDK/client errors are clearer.
        pass

@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider
    model: str
    reasoning_effort: Optional[ReasoningEffort] = None
    max_output_tokens: Optional[int] = None
    base_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        provider = data["provider"]
        model = data.get("model")
        reasoning_effort = data.get("reasoning_effort")

        if provider == "openai":
            model = model or DEFAULT_OPENAI_MODEL
            reasoning_effort = reasoning_effort or DEFAULT_OPENAI_REASONING_EFFORT
        elif provider == "openrouter":
            model = model or DEFAULT_OPENROUTER_MODEL
        else:
            model = model or DEFAULT_OLLAMA_MODEL

        return cls(
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=data.get("max_output_tokens"),
            base_url=data.get("base_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "base_url": self.base_url,
        }


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._provider = config.provider
        self._openrouter_headers: dict[str, str] = {}

        if self._provider == "ollama":
            import ollama  # local dependency

            self._ollama = ollama
            self._openai = None
        elif self._provider in {"openai", "openrouter"}:
            required_key = "OPENAI_API_KEY" if self._provider == "openai" else "OPENROUTER_LAB"
            if not os.environ.get(required_key):
                _maybe_load_dotenv()

            from openai import OpenAI

            kwargs: dict[str, Any] = {}
            if self._provider == "openrouter":
                kwargs["api_key"] = os.environ.get(required_key)
                kwargs["base_url"] = config.base_url or DEFAULT_OPENROUTER_BASE_URL
                referer = os.environ.get("OPENROUTER_SITE_URL")
                title = os.environ.get("OPENROUTER_SITE_NAME")
                if referer:
                    self._openrouter_headers["HTTP-Referer"] = referer
                if title:
                    self._openrouter_headers["X-OpenRouter-Title"] = title
                if self._openrouter_headers:
                    kwargs["default_headers"] = self._openrouter_headers
            elif config.base_url:
                kwargs["base_url"] = config.base_url
            self._openai = OpenAI(**kwargs)
            self._ollama = None
        else:
            raise ValueError(f"Unsupported provider: {self._provider}")

    def _log_llm_start(self, *, kind: str, prompt: str, system: str | None, schema_name: str | None = None) -> float:
        total_chars = len(prompt) + len(system or "")
        extra = f" schema={schema_name}" if schema_name else ""
        print(f"[llm] -> {kind} {self._provider}/{self.config.model}{extra} chars={total_chars}", flush=True)
        return time.monotonic()

    def _log_llm_done(self, *, kind: str, started_at: float, output_len: int, schema_name: str | None = None) -> None:
        elapsed = time.monotonic() - started_at
        extra = f" schema={schema_name}" if schema_name else ""
        print(
            f"[llm] <- {kind} {self._provider}/{self.config.model}{extra} {elapsed:.1f}s chars={output_len}",
            flush=True,
        )

    def _log_llm_retry(self, *, kind: str, schema_name: str | None = None) -> None:
        extra = f" schema={schema_name}" if schema_name else ""
        print(f"[llm] !! retry {kind} {self._provider}/{self.config.model}{extra}", flush=True)

    def _apply_reasoning_options(self, params: dict[str, Any]) -> None:
        effort = self.config.reasoning_effort
        if not effort:
            return

        if self._provider == "openrouter" and self.config.model in CLAUDE_46_MODELS:
            if effort == "none":
                return
            params["reasoning"] = {"enabled": True}
            verbosity = VERBOSITY_BY_REASONING_EFFORT.get(effort)
            if verbosity:
                extra_body = dict(params.get("extra_body") or {})
                extra_body["verbosity"] = verbosity
                params["extra_body"] = extra_body
            return

        params["reasoning"] = {"effort": effort}

    def generate_text(self, *, prompt: str, system: str | None = None) -> str:
        """Return assistant text (no schema enforcement)."""
        started_at = self._log_llm_start(kind="text", prompt=prompt, system=system)
        if self._provider == "ollama":
            full_prompt = prompt if system is None else f"{system}\n\n{prompt}"
            resp = self._ollama.generate(
                model=self.config.model,
                prompt=full_prompt,
            )
            text = resp["response"]
            self._log_llm_done(kind="text", started_at=started_at, output_len=len(text))
            return text

        # OpenAI Responses API
        params: dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
        }
        if system:
            params["instructions"] = system
        self._apply_reasoning_options(params)
        if self.config.max_output_tokens is not None:
            params["max_output_tokens"] = int(self.config.max_output_tokens)

        resp = self._openai.responses.create(**params)
        text = getattr(resp, "output_text", "")
        text = text or ""
        self._log_llm_done(kind="text", started_at=started_at, output_len=len(text))
        return text

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON object; provider enforces JSON/schema when supported."""
        started_at = self._log_llm_start(kind="json", prompt=prompt, system=system, schema_name=schema_name)
        if self._provider == "ollama":
            retry_prompt = prompt
            for attempt in range(2):
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": retry_prompt})

                resp = self._ollama.chat(
                    model=self.config.model,
                    messages=messages,
                    format=schema,
                )
                raw = resp["message"]["content"]
                try:
                    parsed = json.loads(raw)
                    self._log_llm_done(
                        kind="json",
                        started_at=started_at,
                        output_len=len(raw),
                        schema_name=schema_name,
                    )
                    return parsed
                except json.JSONDecodeError as exc:
                    if attempt == 0:
                        self._log_llm_retry(kind="json", schema_name=schema_name)
                        retry_prompt = prompt + JSON_RETRY_INSTRUCTION
                        continue
                    raise ValueError(
                        f"LLM returned invalid JSON: {exc}. Raw content: {raw[:500]}"
                    ) from exc

        params: dict[str, Any] = {
            "model": self.config.model,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        if system:
            params["instructions"] = system
        self._apply_reasoning_options(params)
        if self.config.max_output_tokens is not None:
            params["max_output_tokens"] = int(self.config.max_output_tokens)

        retry_prompt = prompt
        for attempt in range(2):
            params["input"] = retry_prompt
            resp = self._openai.responses.create(**params)
            raw = getattr(resp, "output_text", "") or ""
            try:
                parsed = json.loads(raw)
                self._log_llm_done(
                    kind="json",
                    started_at=started_at,
                    output_len=len(raw),
                    schema_name=schema_name,
                )
                return parsed
            except json.JSONDecodeError as exc:
                if attempt == 0:
                    self._log_llm_retry(kind="json", schema_name=schema_name)
                    retry_prompt = prompt + JSON_RETRY_INSTRUCTION
                    continue
                raise ValueError(f"LLM returned invalid JSON: {exc}. Raw content: {raw[:500]}") from exc
