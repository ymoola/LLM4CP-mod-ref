from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional


LLMProvider = Literal["ollama", "openai"]


@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider
    model: str
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = None
    max_output_tokens: Optional[int] = None
    base_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        return cls(
            provider=data["provider"],
            model=data["model"],
            reasoning_effort=data.get("reasoning_effort"),
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

        if self._provider == "ollama":
            import ollama  # local dependency

            self._ollama = ollama
            self._openai = None
        elif self._provider == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                try:
                    from dotenv import find_dotenv, load_dotenv

                    env_path = find_dotenv(usecwd=True)
                    if env_path:
                        load_dotenv(env_path)
                except Exception:
                    # Don't fail if python-dotenv isn't available; OpenAI SDK will raise a clear error.
                    pass

            from openai import OpenAI

            kwargs: dict[str, Any] = {}
            if config.base_url:
                kwargs["base_url"] = config.base_url
            self._openai = OpenAI(**kwargs)
            self._ollama = None
        else:
            raise ValueError(f"Unsupported provider: {self._provider}")

    def generate_text(self, *, prompt: str, system: str | None = None) -> str:
        """Return assistant text (no schema enforcement)."""
        if self._provider == "ollama":
            full_prompt = prompt if system is None else f"{system}\n\n{prompt}"
            resp = self._ollama.generate(
                model=self.config.model,
                prompt=full_prompt,
            )
            return resp["response"]

        # OpenAI Responses API
        params: dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
        }
        if system:
            params["instructions"] = system
        if self.config.reasoning_effort:
            params["reasoning"] = {"effort": self.config.reasoning_effort}
        if self.config.max_output_tokens is not None:
            params["max_output_tokens"] = int(self.config.max_output_tokens)

        resp = self._openai.responses.create(**params)
        text = getattr(resp, "output_text", "")
        return text or ""

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON object; provider enforces JSON/schema when supported."""
        if self._provider == "ollama":
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = self._ollama.chat(
                model=self.config.model,
                messages=messages,
                format=schema,
            )
            raw = resp["message"]["content"]
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"LLM returned invalid JSON: {exc}. Raw content: {raw[:500]}") from exc

        params: dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
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
        if self.config.reasoning_effort:
            params["reasoning"] = {"effort": self.config.reasoning_effort}
        if self.config.max_output_tokens is not None:
            params["max_output_tokens"] = int(self.config.max_output_tokens)

        resp = self._openai.responses.create(**params)
        raw = getattr(resp, "output_text", "") or ""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}. Raw content: {raw[:500]}") from exc
