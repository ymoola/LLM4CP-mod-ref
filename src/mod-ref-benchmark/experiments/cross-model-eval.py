from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any


THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent
WORKFLOW_DIR = MODREF_DIR / "langgraph_workflow"

if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))
if str(WORKFLOW_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_DIR))

from llm_client import DEFAULT_OPENAI_REASONING_EFFORT  # noqa: E402
from langgraph_workflow.workflow import run_workflow_once  # noqa: E402          


MODEL_PRESETS: list[dict[str, Any]] = [
    {
        "key": "openai_gpt_5_4",
        "label": "OpenAI GPT-5.4",
        "provider": "openai",
        "model": "gpt-5.4",
        "reasoning_effort": DEFAULT_OPENAI_REASONING_EFFORT,
        "docs_url": "https://platform.openai.com/docs/models/compare",
    },
    {
        "key": "openrouter_qwen3_next_80b_a3b_instruct",
        "label": "OpenRouter Qwen3-Next 80B A3B Instruct",
        "provider": "openrouter",
        "model": "qwen/qwen3-next-80b-a3b-instruct",
        "reasoning_effort": None,
        "docs_url": "https://openrouter.ai/qwen/qwen3-next-80b-a3b-instruct/providers",
    },
    {
        "key": "openrouter_qwen3_5_27b_reasoning_off",
        "label": "OpenRouter Qwen3.5 27B (reasoning off)",
        "provider": "openrouter",
        "model": "qwen/qwen3.5-27b",
        "reasoning_effort": "none",
        "docs_url": "https://openrouter.ai/compare/qwen/qwen3.5-27b/z-ai/glm-4.7-flash",
    },
    {
        "key": "openrouter_gemini_3_1_flash_lite_preview",
        "label": "OpenRouter Gemini 3.1 Flash Lite Preview",
        "provider": "openrouter",
        "model": "google/gemini-3.1-flash-lite-preview",
        "reasoning_effort": None,
        "docs_url": None,
    },
    {
        "key": "openrouter_claude_opus_4_6_high_reasoning",
        "label": "OpenRouter Claude Opus 4.6 (high reasoning)",
        "provider": "openrouter",
        "model": "anthropic/claude-opus-4.6",
        "reasoning_effort": "high",
        "docs_url": "https://openrouter.ai/anthropic/claude-opus-4.6/api",
    },
    {
        "key": "openrouter_qwen3_5_9b_reasoning_off",
        "label": "OpenRouter Qwen3.5 9B (reasoning off)",
        "provider": "openrouter",
        "model": "qwen/qwen3.5-9b",
        "reasoning_effort": "none",
        "docs_url": "https://openrouter.ai/compare/black-forest-labs/flux.2-max/qwen/qwen3.5-9b",
    },
]


def _ignore_copy(_: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".DS_Store", "results", "generated_model.py"}
    return {name for name in names if name in ignored}


def _iter_cases(problems_root: Path, only_problem: str | None, only_cr: str | None):
    for problem_dir in sorted(problems_root.iterdir()):
        if not problem_dir.is_dir() or not problem_dir.name.startswith("problem"):
            continue
        if only_problem and problem_dir.name != only_problem:
            continue

        for cr_dir in sorted(problem_dir.iterdir()):
            if not cr_dir.is_dir() or not cr_dir.name.startswith("CR"):
                continue
            if only_cr and cr_dir.name != only_cr:
                continue
            yield problem_dir, cr_dir


def _prepare_case_workspace(problem_dir: Path, cr_dir: Path, workspace_root: Path) -> Path:
    if workspace_root.exists():
        shutil.rmtree(workspace_root)

    workspace_problem_dir = workspace_root / problem_dir.name
    workspace_problem_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(problem_dir / "base", workspace_problem_dir / "base", ignore=_ignore_copy)
    shutil.copytree(cr_dir, workspace_problem_dir / cr_dir.name, ignore=_ignore_copy)
    return workspace_problem_dir


def _build_llm_config(preset: dict[str, Any], max_output_tokens: int | None) -> dict[str, Any]:
    return {
        "provider": preset["provider"],
        "model": preset["model"],
        "reasoning_effort": preset.get("reasoning_effort"),
        "max_output_tokens": max_output_tokens,
    }


def _summarize_case(
    *,
    preset: dict[str, Any],
    problem_name: str,
    cr_name: str,
    case_dir: Path,
    result: dict[str, Any] | None,
    run_log: dict[str, Any] | None,
    log_path: Path | None,
    error: Exception | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "model_key": preset["key"],
        "model_label": preset["label"],
        "provider": preset["provider"],
        "model": preset["model"],
        "reasoning_effort": preset.get("reasoning_effort"),
        "problem": problem_name,
        "cr": cr_name,
        "case_dir": str(case_dir.resolve()),
        "workspace_problem_path": str((case_dir / "workspace" / problem_name).resolve()),
        "docs_url": preset.get("docs_url"),
    }

    if error is not None:
        summary.update(
            {
                "status": "fail",
                "stage": "runner",
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
        )
        return summary

    unit_test_result = (result or {}).get("unit_test_result") or {}
    summary.update(
        {
            "status": unit_test_result.get("status", "fail"),
            "planner_validator_status": (result or {}).get("planner_validator_status"),
            "validator_status": (result or {}).get("validator_status"),
            "termination_reason": (result or {}).get("termination_reason"),
            "loop_count": (result or {}).get("loop_count"),
            "clarification_turn_count": (result or {}).get("clarification_turn_count"),
            "exec_error": (result or {}).get("exec_error"),
            "unit_test_result_path": (result or {}).get("unit_test_result_path"),
            "workflow_log_path": str(log_path.resolve()) if log_path else None,
            "generated_model_path": (run_log or {}).get("generated_model_path"),
        }
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the LangGraph workflow across all problems/CRs for a fixed cross-model evaluation set."
    )
    parser.add_argument(
        "--problems-root",
        default=str((MODREF_DIR / "problems").resolve()),
        help="Root directory containing problem folders (default: src/mod-ref-benchmark/problems).",
    )
    parser.add_argument(
        "--output-root",
        default=str((THIS_DIR / "results").resolve()),
        help="Output root for cross-model evaluation results (default: src/mod-ref-benchmark/experiments/results).",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens passed through to the LLM client.",
    )
    parser.add_argument(
        "--max-planner-validation-error-loops",
        type=int,
        default=5,
        help="Maximum number of planner-validation retries before failing early.",
    )
    parser.add_argument(
        "--max-exec-error-loops",
        type=int,
        default=5,
        help="Maximum number of execution-error retries before failing.",
    )
    parser.add_argument(
        "--max-validation-error-loops",
        type=int,
        default=5,
        help="Maximum number of validation-error retries before forcing unit test on the current executable model.",
    )
    parser.add_argument(
        "--executor-timeout",
        type=int,
        default=30,
        help="Per execution timeout in seconds for generated models (0 disables timeout).",
    )
    parser.add_argument(
        "--only-problem",
        help="Optional: run only a specific problem folder name (e.g., problem1).",
    )
    parser.add_argument(
        "--only-cr",
        help="Optional: run only a specific CR folder name (e.g., CR1).",
    )
    parser.add_argument(
        "--only-model",
        action="append",
        help="Optional preset key to run. Repeat to run more than one model.",
    )
    args = parser.parse_args()

    selected_presets = [
        preset for preset in MODEL_PRESETS if not args.only_model or preset["key"] in set(args.only_model)
    ]
    if not selected_presets:
        raise ValueError("No model presets selected. Check --only-model values.")

    problems_root = Path(args.problems_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    eval_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    eval_root = output_root / eval_timestamp
    eval_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": eval_timestamp,
        "problems_root": str(problems_root),
        "output_root": str(eval_root),
        "hitl_enabled": False,
        "max_planner_validation_error_loops": args.max_planner_validation_error_loops,
        "max_exec_error_loops": args.max_exec_error_loops,
        "max_validation_error_loops": args.max_validation_error_loops,
        "executor_timeout": args.executor_timeout,
        "max_output_tokens": args.max_output_tokens,
        "selected_models": selected_presets,
    }
    (eval_root / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2))

    all_results: list[dict[str, Any]] = []

    for preset in selected_presets:
        preset_dir = eval_root / preset["key"]
        preset_dir.mkdir(parents=True, exist_ok=True)
        model_results: list[dict[str, Any]] = []

        llm_config = _build_llm_config(preset, args.max_output_tokens)
        print(f"[cross-model-eval] Running preset {preset['key']} -> {preset['model']}", flush=True)

        for problem_dir, cr_dir in _iter_cases(problems_root, args.only_problem, args.only_cr):
            case_dir = preset_dir / problem_dir.name / cr_dir.name
            case_dir.mkdir(parents=True, exist_ok=True)
            workspace_problem_dir = _prepare_case_workspace(problem_dir, cr_dir, case_dir / "workspace")

            print(
                f"[cross-model-eval] Running {preset['key']} on {problem_dir.name}/{cr_dir.name} ...",
                flush=True,
            )
            try:
                result, run_log, log_path = run_workflow_once(
                    problem_path=str(workspace_problem_dir),
                    cr=cr_dir.name,
                    llm_config=llm_config,
                    max_planner_validation_error_loops=args.max_planner_validation_error_loops,
                    max_exec_error_loops=args.max_exec_error_loops,
                    max_validation_error_loops=args.max_validation_error_loops,
                    executor_timeout=args.executor_timeout,
                    run_output_dir=case_dir,
                    hitl_enabled=False,
                )
                case_summary = _summarize_case(
                    preset=preset,
                    problem_name=problem_dir.name,
                    cr_name=cr_dir.name,
                    case_dir=case_dir,
                    result=result,
                    run_log=run_log,
                    log_path=log_path,
                )
            except Exception as exc:
                case_summary = _summarize_case(
                    preset=preset,
                    problem_name=problem_dir.name,
                    cr_name=cr_dir.name,
                    case_dir=case_dir,
                    result=None,
                    run_log=None,
                    log_path=None,
                    error=exc,
                )

            (case_dir / "case_summary.json").write_text(json.dumps(case_summary, indent=2))
            model_results.append(case_summary)
            all_results.append(case_summary)

        model_summary = {
            "model_key": preset["key"],
            "model_label": preset["label"],
            "provider": preset["provider"],
            "model": preset["model"],
            "reasoning_effort": preset.get("reasoning_effort"),
            "docs_url": preset.get("docs_url"),
            "counts": {
                "total": len(model_results),
                "pass": sum(1 for item in model_results if item.get("status") == "pass"),
                "fail": sum(1 for item in model_results if item.get("status") == "fail"),
            },
            "results": model_results,
        }
        (preset_dir / "model_summary.json").write_text(json.dumps(model_summary, indent=2))

    overall_summary = {
        "timestamp": eval_timestamp,
        "counts": {
            "total": len(all_results),
            "pass": sum(1 for item in all_results if item.get("status") == "pass"),
            "fail": sum(1 for item in all_results if item.get("status") == "fail"),
        },
        "selected_models": [
            {
                "key": preset["key"],
                "label": preset["label"],
                "provider": preset["provider"],
                "model": preset["model"],
                "reasoning_effort": preset.get("reasoning_effort"),
                "docs_url": preset.get("docs_url"),
            }
            for preset in selected_presets
        ],
        "results": all_results,
    }
    summary_path = eval_root / "cross_model_eval_summary.json"
    summary_path.write_text(json.dumps(overall_summary, indent=2))
    print(f"[cross-model-eval] Done. Summary saved to {summary_path}", flush=True)


if __name__ == "__main__":
    main()
