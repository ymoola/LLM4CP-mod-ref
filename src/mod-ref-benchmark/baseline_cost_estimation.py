from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from llm_prompts import build_single_shot_prompt, extract_output_keys

OPENAI_PRICING_SOURCE_URL = "https://developers.openai.com/api/docs/models/compare"

@dataclass(frozen=True)
class PricingInfo:
    provider: str
    model: str
    source: str
    source_url: str | None
    prompt_cost_per_token: Decimal
    completion_cost_per_token: Decimal
    request_cost: Decimal
    internal_reasoning_cost_per_token: Decimal | None
    available: bool
    note: str | None = None
    raw_pricing: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "source": self.source,
            "source_url": self.source_url,
            "available": self.available,
            "note": self.note,
            "prompt_cost_per_token": _money_to_float(self.prompt_cost_per_token),
            "completion_cost_per_token": _money_to_float(self.completion_cost_per_token),
            "request_cost": _money_to_float(self.request_cost),
            "internal_reasoning_cost_per_token": _money_to_float(self.internal_reasoning_cost_per_token),
            "prompt_cost_per_million": _money_to_float(self.prompt_cost_per_token * Decimal(1_000_000)),
            "completion_cost_per_million": _money_to_float(self.completion_cost_per_token * Decimal(1_000_000)),
            "internal_reasoning_cost_per_million": _money_to_float(
                self.internal_reasoning_cost_per_token * Decimal(1_000_000)
                if self.internal_reasoning_cost_per_token is not None
                else None
            ),
            "raw_pricing": self.raw_pricing,
        }


@dataclass(frozen=True)
class CasePromptInfo:
    problem: str
    cr: str
    prompt: str
    expected_output_keys: list[str]
    prompt_path_inputs: dict[str, str]



def _decimal_from_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")



def _money_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 8)



def load_case_prompt_info(problem_dir: Path, cr_dir: Path) -> CasePromptInfo:
    base_dir = problem_dir / "base"
    base_desc_path = base_dir / "problem_desc.txt"
    base_model_path = base_dir / "reference_model.py"
    cr_desc_path = cr_dir / "desc.json"

    base_nl_description = base_desc_path.read_text()
    base_reference_code = base_model_path.read_text()
    cr_desc = json.loads(cr_desc_path.read_text())
    expected_output_keys = extract_output_keys(cr_desc.get("ref_sol_format", {}))
    prompt = build_single_shot_prompt(
        base_nl_description=base_nl_description,
        base_reference_code=base_reference_code,
        cr_desc=cr_desc,
        expected_output_keys=expected_output_keys,
    )
    return CasePromptInfo(
        problem=problem_dir.name,
        cr=cr_dir.name,
        prompt=prompt,
        expected_output_keys=expected_output_keys,
        prompt_path_inputs={
            "base_desc_path": str(base_desc_path),
            "base_model_path": str(base_model_path),
            "cr_desc_path": str(cr_desc_path),
        },
    )



def count_prompt_tokens(*, provider: str, model: str, prompt: str) -> tuple[int, str]:
    try:
        import tiktoken
    except ImportError as exc:
        raise RuntimeError(
            "Cost estimation requires the 'tiktoken' package. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    if provider == "openai":
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(prompt)), f"tiktoken:{model}"
        except Exception:
            pass

    encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(prompt)), "tiktoken:o200k_base_approx"



def _heuristic_output_tokens(input_tokens: int) -> tuple[int, int]:
    expected = max(800, min(4000, int(math.ceil(0.35 * input_tokens))))
    upper = max(1500, min(8000, int(math.ceil(0.75 * input_tokens))))
    return expected, upper



def _resolve_local_preset_pricing(spec: dict[str, Any]) -> PricingInfo | None:
    pricing = spec.get("pricing_per_million")
    if pricing is None:
        return None

    million = Decimal(1_000_000)
    prompt_per_million = _decimal_from_value(pricing["prompt"])
    completion_per_million = _decimal_from_value(pricing["completion"])
    request_cost = _decimal_from_value(pricing.get("request", 0))
    return PricingInfo(
        provider=spec["provider"],
        model=spec["model"],
        source="preset_local_table",
        source_url=spec.get("pricing_source_url") or spec.get("docs_url") or OPENAI_PRICING_SOURCE_URL,
        prompt_cost_per_token=prompt_per_million / million,
        completion_cost_per_token=completion_per_million / million,
        request_cost=request_cost,
        internal_reasoning_cost_per_token=None,
        available=True,
        note="Pricing uses the local preset table maintained in the repo.",
        raw_pricing={
            "prompt_per_million": _money_to_float(prompt_per_million),
            "completion_per_million": _money_to_float(completion_per_million),
            "request": _money_to_float(request_cost),
        },
    )

def resolve_pricing_for_models(model_specs: list[dict[str, Any]]) -> dict[str, PricingInfo]:
    pricing_map: dict[str, PricingInfo] = {}

    for spec in model_specs:
        key = spec["key"]
        provider = spec["provider"]
        model = spec["model"]
        local_pricing = _resolve_local_preset_pricing(spec)
        if local_pricing is not None:
            pricing_map[key] = local_pricing
        else:
            pricing_map[key] = PricingInfo(
                provider=provider,
                model=model,
                source="pricing_unavailable",
                source_url=spec.get("docs_url"),
                prompt_cost_per_token=Decimal("0"),
                completion_cost_per_token=Decimal("0"),
                request_cost=Decimal("0"),
                internal_reasoning_cost_per_token=None,
                available=False,
                note=f"No local pricing entry for provider '{provider}' model '{model}'.",
                raw_pricing=None,
            )
    return pricing_map



def _cost_breakdown(*, pricing: PricingInfo, input_tokens: int, output_tokens: int) -> Decimal | None:
    if not pricing.available:
        return None
    return (
        pricing.prompt_cost_per_token * Decimal(input_tokens)
        + pricing.completion_cost_per_token * Decimal(output_tokens)
        + pricing.request_cost
    )



def _compact_cost(value: Decimal | None) -> float | None:
    return _money_to_float(value)



def estimate_baseline_run_cost(
    *,
    cases: list[tuple[Path, Path]],
    model_specs: list[dict[str, Any]],
    max_output_tokens: int | None,
) -> dict[str, Any]:
    pricing_by_key = resolve_pricing_for_models(model_specs)

    estimate: dict[str, Any] = {
        "generated_at": dt.datetime.now().isoformat(),
        "max_output_tokens": max_output_tokens,
        "heuristics": {
            "expected_output_tokens": "max(800, min(4000, ceil(0.35 * input_tokens)))",
            "upper_output_tokens": "max(1500, min(8000, ceil(0.75 * input_tokens))) unless max_output_tokens is set",
            "notes": [
                "Prompt tokens are counted from the fully rendered baseline prompt.",
                "OpenAI token counts use tiktoken directly.",
                "OpenRouter token counts use a GPT-family fallback encoding and should be treated as approximate.",
                "Cost estimates exclude provider-specific hidden reasoning-token charges unless already reflected in published completion pricing.",
            ],
        },
        "models": [],
        "totals": {},
    }

    total_invocations = 0
    overall_input_tokens = 0
    overall_expected_output_tokens = 0
    overall_upper_output_tokens = 0
    overall_lower_cost = Decimal("0")
    overall_expected_cost = Decimal("0")
    overall_upper_cost = Decimal("0")
    overall_cost_complete = True
    unpriced_models: list[str] = []

    prompt_cache: dict[tuple[str, str], dict[str, Any]] = {}

    for spec in model_specs:
        model_key = spec["key"]
        pricing = pricing_by_key[model_key]
        model_input_tokens = 0
        model_expected_output_tokens = 0
        model_upper_output_tokens = 0
        model_lower_cost = Decimal("0")
        model_expected_cost = Decimal("0")
        model_upper_cost = Decimal("0")
        model_cost_complete = pricing.available
        token_methods: set[str] = set()

        for problem_dir, cr_dir in cases:
            cache_key = (problem_dir.name, cr_dir.name)
            case_prompt_data = prompt_cache.get(cache_key)
            if case_prompt_data is None:
                try:
                    prompt_info = load_case_prompt_info(problem_dir, cr_dir)
                    case_prompt_data = {
                        "problem": prompt_info.problem,
                        "cr": prompt_info.cr,
                        "prompt": prompt_info.prompt,
                        "expected_output_keys": prompt_info.expected_output_keys,
                        "prompt_path_inputs": prompt_info.prompt_path_inputs,
                        "error": None,
                    }
                except Exception as exc:
                    case_prompt_data = {
                        "problem": problem_dir.name,
                        "cr": cr_dir.name,
                        "prompt": None,
                        "expected_output_keys": [],
                        "prompt_path_inputs": {},
                        "error": str(exc),
                    }
                prompt_cache[cache_key] = case_prompt_data

            if case_prompt_data["error"]:
                model_cost_complete = False
                continue

            input_tokens, token_method = count_prompt_tokens(
                provider=spec["provider"],
                model=spec["model"],
                prompt=case_prompt_data["prompt"],
            )
            token_methods.add(token_method)
            heuristic_expected, heuristic_upper = _heuristic_output_tokens(input_tokens)
            expected_output_tokens = min(heuristic_expected, max_output_tokens) if max_output_tokens is not None else heuristic_expected
            upper_output_tokens = max_output_tokens if max_output_tokens is not None else heuristic_upper

            lower_cost = _cost_breakdown(pricing=pricing, input_tokens=input_tokens, output_tokens=0)
            expected_cost = _cost_breakdown(
                pricing=pricing,
                input_tokens=input_tokens,
                output_tokens=expected_output_tokens,
            )
            upper_cost = _cost_breakdown(
                pricing=pricing,
                input_tokens=input_tokens,
                output_tokens=upper_output_tokens,
            )

            model_input_tokens += input_tokens
            model_expected_output_tokens += expected_output_tokens
            model_upper_output_tokens += upper_output_tokens
            total_invocations += 1

            if lower_cost is not None and expected_cost is not None and upper_cost is not None:
                model_lower_cost += lower_cost
                model_expected_cost += expected_cost
                model_upper_cost += upper_cost
            else:
                model_cost_complete = False

        if model_cost_complete:
            overall_lower_cost += model_lower_cost
            overall_expected_cost += model_expected_cost
            overall_upper_cost += model_upper_cost
        else:
            overall_cost_complete = False
            if not pricing.available:
                unpriced_models.append(model_key)

        overall_input_tokens += model_input_tokens
        overall_expected_output_tokens += model_expected_output_tokens
        overall_upper_output_tokens += model_upper_output_tokens

        estimate["models"].append(
            {
                "model_key": model_key,
                "model_label": spec["label"],
                "provider": spec["provider"],
                "model": spec["model"],
                "reasoning_effort": spec.get("reasoning_effort"),
                "docs_url": spec.get("docs_url"),
                "pricing": pricing.to_dict(),
                "token_count_methods": sorted(token_methods),
                "counts": {
                    "cases": len(cases),
                },
                "totals": {
                    "input_tokens": model_input_tokens,
                    "expected_output_tokens": model_expected_output_tokens,
                    "upper_output_tokens": model_upper_output_tokens,
                    "lower_cost": _compact_cost(model_lower_cost) if model_cost_complete else None,
                    "expected_cost": _compact_cost(model_expected_cost) if model_cost_complete else None,
                    "upper_cost": _compact_cost(model_upper_cost) if model_cost_complete else None,
                    "cost_complete": model_cost_complete,
                },
            }
        )

    estimate["totals"] = {
        "models": len(model_specs),
        "selected_cases": len(cases),
        "invocations": total_invocations,
        "input_tokens": overall_input_tokens,
        "expected_output_tokens": overall_expected_output_tokens,
        "upper_output_tokens": overall_upper_output_tokens,
        "lower_cost": _compact_cost(overall_lower_cost) if overall_cost_complete else None,
        "expected_cost": _compact_cost(overall_expected_cost) if overall_cost_complete else None,
        "upper_cost": _compact_cost(overall_upper_cost) if overall_cost_complete else None,
        "cost_complete": overall_cost_complete,
        "unpriced_models": sorted(set(unpriced_models)),
    }
    return estimate
