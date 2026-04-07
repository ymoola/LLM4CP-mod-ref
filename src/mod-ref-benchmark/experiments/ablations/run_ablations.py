from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = THIS_DIR.parent
MODREF_DIR = EXPERIMENTS_DIR.parent
WORKFLOW_DIR = MODREF_DIR / "langgraph_workflow"

if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))
if str(WORKFLOW_DIR) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_DIR))

from langgraph_workflow.workflow import run_workflow_once  # noqa: E402
from model_presets import get_model_preset_by_key  # noqa: E402
from variant_presets import select_ablation_variants  # noqa: E402

DEFAULT_ABLATION_MODEL_KEY = "openrouter_gpt_5_4_mini"


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


def _resolve_variant_config(variant: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    loop_overrides = dict(variant.get("loop_overrides") or {})
    return {
        "enable_planner_validator": variant["enable_planner_validator"],
        "enable_final_validator": variant["enable_final_validator"],
        "max_planner_validation_error_loops": loop_overrides.get(
            "max_planner_validation_error_loops", args.max_planner_validation_error_loops
        ),
        "max_exec_error_loops": loop_overrides.get("max_exec_error_loops", args.max_exec_error_loops),
        "max_validation_error_loops": loop_overrides.get(
            "max_validation_error_loops", args.max_validation_error_loops
        ),
    }


def _summarize_case(
    *,
    preset: dict[str, Any],
    variant: dict[str, Any],
    effective_config: dict[str, Any],
    problem_name: str,
    cr_name: str,
    case_dir: Path,
    elapsed_seconds: float,
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
        "variant_key": variant["key"],
        "variant_label": variant["label"],
        "variant_description": variant["description"],
        "effective_variant_config": effective_config,
        "problem": problem_name,
        "cr": cr_name,
        "runtime_seconds": round(elapsed_seconds, 6),
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
            "planner_validation_error_count": (result or {}).get("planner_validation_error_count"),
            "exec_error_count": (result or {}).get("exec_error_count"),
            "validation_error_count": (result or {}).get("validation_error_count"),
            "exec_error": (result or {}).get("exec_error"),
            "unit_test_result_path": (result or {}).get("unit_test_result_path"),
            "workflow_log_path": str(log_path.resolve()) if log_path else None,
            "generated_model_path": (run_log or {}).get("generated_model_path"),
        }
    )
    return summary


def _build_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(results),
        "pass": sum(1 for item in results if item.get("status") == "pass"),
        "fail": sum(1 for item in results if item.get("status") == "fail"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LangGraph workflow ablation variants across all problems/CRs for a fixed model."
    )
    parser.add_argument(
        "--problems-root",
        default=str((MODREF_DIR / "problems").resolve()),
        help="Root directory containing problem folders (default: src/mod-ref-benchmark/problems).",
    )
    parser.add_argument(
        "--output-root",
        default=str((THIS_DIR / "results").resolve()),
        help="Output root for ablation results (default: src/mod-ref-benchmark/experiments/ablations/results).",
    )
    parser.add_argument(
        "--model-key",
        default=DEFAULT_ABLATION_MODEL_KEY,
        help=f"Model preset key to use for the ablation study (default: {DEFAULT_ABLATION_MODEL_KEY}).",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens passed through to the LLM client.",
    )
    parser.add_argument(
        "--max-planner-validation-error-loops",
        type=int,
        default=3,
        help="Baseline planner-validator retry budget for the full workflow (default: 3).",
    )
    parser.add_argument(
        "--max-exec-error-loops",
        type=int,
        default=8,
        help="Baseline execution-error retry budget for the full workflow (default: 8).",
    )
    parser.add_argument(
        "--max-validation-error-loops",
        type=int,
        default=5,
        help="Baseline final-validator retry budget for the full workflow (default: 5).",
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
        "--only-variant",
        action="append",
        help="Optional ablation variant key to run. Repeat to run more than one variant.",
    )
    args = parser.parse_args()

    preset = get_model_preset_by_key(args.model_key)
    if preset is None:
        raise ValueError(f"Unknown model preset key: {args.model_key}")

    selected_variants = select_ablation_variants(args.only_variant)
    problems_root = Path(args.problems_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    experiment_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    experiment_root = output_root / experiment_timestamp
    experiment_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": experiment_timestamp,
        "problems_root": str(problems_root),
        "output_root": str(experiment_root),
        "model": preset,
        "hitl_enabled": False,
        "base_loop_budgets": {
            "max_planner_validation_error_loops": args.max_planner_validation_error_loops,
            "max_exec_error_loops": args.max_exec_error_loops,
            "max_validation_error_loops": args.max_validation_error_loops,
        },
        "executor_timeout": args.executor_timeout,
        "max_output_tokens": args.max_output_tokens,
        "variants": [
            {
                **variant,
                "effective_config": _resolve_variant_config(variant, args),
            }
            for variant in selected_variants
        ],
    }
    (experiment_root / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2))

    llm_config = _build_llm_config(preset, args.max_output_tokens)
    model_root = experiment_root / preset["key"]
    model_root.mkdir(parents=True, exist_ok=True)

    all_results: list[dict[str, Any]] = []
    variant_summaries: list[dict[str, Any]] = []

    for variant in selected_variants:
        effective_config = _resolve_variant_config(variant, args)
        variant_dir = model_root / variant["key"]
        variant_dir.mkdir(parents=True, exist_ok=True)
        variant_results: list[dict[str, Any]] = []

        print(
            f"[ablations] Running variant {variant['key']} with model {preset['key']} -> {preset['model']}",
            flush=True,
        )

        for problem_dir, cr_dir in _iter_cases(problems_root, args.only_problem, args.only_cr):
            case_dir = variant_dir / problem_dir.name / cr_dir.name
            case_dir.mkdir(parents=True, exist_ok=True)
            workspace_problem_dir = _prepare_case_workspace(problem_dir, cr_dir, case_dir / "workspace")

            print(
                f"[ablations] Running {variant['key']} on {problem_dir.name}/{cr_dir.name} ...",
                flush=True,
            )

            started = time.perf_counter()
            try:
                result, run_log, log_path = run_workflow_once(
                    problem_path=str(workspace_problem_dir),
                    cr=cr_dir.name,
                    llm_config=llm_config,
                    max_planner_validation_error_loops=effective_config["max_planner_validation_error_loops"],
                    max_exec_error_loops=effective_config["max_exec_error_loops"],
                    max_validation_error_loops=effective_config["max_validation_error_loops"],
                    executor_timeout=args.executor_timeout,
                    run_output_dir=case_dir,
                    hitl_enabled=False,
                    enable_planner_validator=effective_config["enable_planner_validator"],
                    enable_final_validator=effective_config["enable_final_validator"],
                )
                elapsed = time.perf_counter() - started
                case_summary = _summarize_case(
                    preset=preset,
                    variant=variant,
                    effective_config=effective_config,
                    problem_name=problem_dir.name,
                    cr_name=cr_dir.name,
                    case_dir=case_dir,
                    elapsed_seconds=elapsed,
                    result=result,
                    run_log=run_log,
                    log_path=log_path,
                )
            except Exception as exc:
                elapsed = time.perf_counter() - started
                case_summary = _summarize_case(
                    preset=preset,
                    variant=variant,
                    effective_config=effective_config,
                    problem_name=problem_dir.name,
                    cr_name=cr_dir.name,
                    case_dir=case_dir,
                    elapsed_seconds=elapsed,
                    result=None,
                    run_log=None,
                    log_path=None,
                    error=exc,
                )

            (case_dir / "case_summary.json").write_text(json.dumps(case_summary, indent=2))
            variant_results.append(case_summary)
            all_results.append(case_summary)

        variant_summary = {
            "model_key": preset["key"],
            "model_label": preset["label"],
            "provider": preset["provider"],
            "model": preset["model"],
            "reasoning_effort": preset.get("reasoning_effort"),
            "variant_key": variant["key"],
            "variant_label": variant["label"],
            "variant_description": variant["description"],
            "effective_variant_config": effective_config,
            "counts": _build_counts(variant_results),
            "results": variant_results,
        }
        (variant_dir / "variant_summary.json").write_text(json.dumps(variant_summary, indent=2))
        variant_summaries.append(variant_summary)

    overall_summary = {
        "timestamp": experiment_timestamp,
        "model": {
            "key": preset["key"],
            "label": preset["label"],
            "provider": preset["provider"],
            "model": preset["model"],
            "reasoning_effort": preset.get("reasoning_effort"),
            "docs_url": preset.get("docs_url"),
        },
        "base_loop_budgets": manifest["base_loop_budgets"],
        "executor_timeout": args.executor_timeout,
        "counts": _build_counts(all_results),
        "variants": [
            {
                "variant_key": summary["variant_key"],
                "variant_label": summary["variant_label"],
                "variant_description": summary["variant_description"],
                "effective_variant_config": summary["effective_variant_config"],
                "counts": summary["counts"],
            }
            for summary in variant_summaries
        ],
        "results": all_results,
    }
    summary_path = experiment_root / "ablation_summary.json"
    summary_path.write_text(json.dumps(overall_summary, indent=2))
    print(f"[ablations] Done. Summary saved to {summary_path}", flush=True)


if __name__ == "__main__":
    main()
