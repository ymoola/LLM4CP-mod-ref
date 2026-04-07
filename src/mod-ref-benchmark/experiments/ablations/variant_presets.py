from __future__ import annotations

from typing import Any


ABLATION_VARIANTS: list[dict[str, Any]] = [
    {
        "key": "full_workflow",
        "label": "Full Workflow",
        "description": "Parser, planner, planner validator, modifier, executor, validator, and unit test with the standard retry budgets.",
        "enable_planner_validator": True,
        "enable_final_validator": True,
        "loop_overrides": {},
    },
    {
        "key": "no_planner_validator",
        "label": "No Planner Validator",
        "description": "Removes the planner validator stage while preserving executor and final validator feedback loops.",
        "enable_planner_validator": False,
        "enable_final_validator": True,
        "loop_overrides": {},
    },
    {
        "key": "no_final_validator",
        "label": "No Final Validator",
        "description": "Skips the final validator and runs the unit test immediately after a successful execution.",
        "enable_planner_validator": True,
        "enable_final_validator": False,
        "loop_overrides": {},
    },
    {
        "key": "no_planner_validator_loops",
        "label": "No Planner Validator Loops",
        "description": "Keeps the planner validator but disables planner-validator retries after the first failed review.",
        "enable_planner_validator": True,
        "enable_final_validator": True,
        "loop_overrides": {"max_planner_validation_error_loops": 0},
    },
    {
        "key": "no_final_validator_loops",
        "label": "No Final Validator Loops",
        "description": "Keeps the final validator but disables modifier retries after validator feedback.",
        "enable_planner_validator": True,
        "enable_final_validator": True,
        "loop_overrides": {"max_validation_error_loops": 0},
    },
    {
        "key": "no_executor_loops",
        "label": "No Executor Loops",
        "description": "Keeps execution feedback but disables retries after the first execution failure.",
        "enable_planner_validator": True,
        "enable_final_validator": True,
        "loop_overrides": {"max_exec_error_loops": 0},
    },
    {
        "key": "planner_modifier_only",
        "label": "Planner + Modifier Only",
        "description": "Uses parser, planner, modifier, executor, and unit test only; both validators are disabled.",
        "enable_planner_validator": False,
        "enable_final_validator": False,
        "loop_overrides": {},
    },
]


def select_ablation_variants(only_keys: list[str] | None = None) -> list[dict[str, Any]]:
    if not only_keys:
        return [dict(variant) for variant in ABLATION_VARIANTS]

    requested = set(only_keys)
    selected = [dict(variant) for variant in ABLATION_VARIANTS if variant["key"] in requested]
    missing = sorted(requested - {variant["key"] for variant in selected})
    if missing:
        raise ValueError(f"Unknown ablation variant keys: {missing}")
    return selected
