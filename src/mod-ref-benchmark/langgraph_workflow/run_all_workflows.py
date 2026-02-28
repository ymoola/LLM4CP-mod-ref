from __future__ import annotations

import argparse
import datetime
import json
import sys
import traceback
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
MODREF_DIR = THIS_DIR.parent  # src/mod-ref-benchmark
if str(MODREF_DIR) not in sys.path:
    sys.path.insert(0, str(MODREF_DIR))

from workflow import build_llm_config, run_workflow_once  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run LangGraph workflow across all problems/CRs.")
    parser.add_argument(
        "--problems-root",
        default=str((MODREF_DIR / "problems").resolve()),
        help="Root directory containing problem folders (default: src/mod-ref-benchmark/problems).",
    )
    parser.add_argument(
        "--output-root",
        default=str((THIS_DIR / "results").resolve()),
        help="Output root for workflow batch results (default: src/mod-ref-benchmark/langgraph_workflow/results).",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai"],
        default="openai",
        help="LLM provider to use.",
    )
    parser.add_argument(
        "--model-name",
        default="gpt-oss:20b",
        help="Model name (OpenAI default alias maps to gpt-5-mini-2025-08-07).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        help="Optional OpenAI reasoning effort.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens for OpenAI.",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=5,
        help="Maximum modifier/executor/validator loops before stopping.",
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

    args = parser.parse_args()

    problems_root = Path(args.problems_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    llm_config = build_llm_config(
        provider=args.provider,
        model_name=args.model_name,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )

    all_results: list[dict[str, Any]] = []

    for problem_dir in sorted(problems_root.iterdir()):
        if not problem_dir.is_dir() or not problem_dir.name.startswith("problem"):
            continue
        if args.only_problem and problem_dir.name != args.only_problem:
            continue

        for cr_dir in sorted(problem_dir.iterdir()):
            if not cr_dir.is_dir() or not cr_dir.name.startswith("CR"):
                continue
            if args.only_cr and cr_dir.name != args.only_cr:
                continue

            case_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            case_output_dir = output_root / problem_dir.name / cr_dir.name / case_timestamp
            case_output_dir.mkdir(parents=True, exist_ok=True)

            print(f"[workflow-batch] Running {problem_dir.name}/{cr_dir.name} ...")
            try:
                result, run_log, log_path = run_workflow_once(
                    problem_path=str(problem_dir),
                    cr=cr_dir.name,
                    llm_config=llm_config,
                    max_loops=args.max_loops,
                    executor_timeout=args.executor_timeout,
                    run_output_dir=case_output_dir,
                )
                all_results.append(
                    {
                        "problem": problem_dir.name,
                        "cr": cr_dir.name,
                        "status": result.get("unit_test_result", {}).get("status", "fail"),
                        "validator_status": result.get("validator_status"),
                        "termination_reason": result.get("termination_reason"),
                        "loop_count": result.get("loop_count"),
                        "exec_error": result.get("exec_error"),
                        "unit_test_result_path": result.get("unit_test_result_path"),
                        "workflow_log_path": str(log_path),
                        "run_output_dir": str(case_output_dir),
                        "generated_model_path": run_log.get("generated_model_path"),
                    }
                )
            except Exception as e:
                all_results.append(
                    {
                        "problem": problem_dir.name,
                        "cr": cr_dir.name,
                        "status": "fail",
                        "stage": "runner",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "run_output_dir": str(case_output_dir),
                    }
                )

    summary_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    summary_path = output_root / f"workflow_summary_{summary_timestamp}.json"
    summary = {
        "timestamp": summary_timestamp,
        "llm_config": llm_config,
        "max_loops": args.max_loops,
        "executor_timeout": args.executor_timeout,
        "counts": {
            "total": len(all_results),
            "pass": sum(1 for r in all_results if r.get("status") == "pass"),
            "fail": sum(1 for r in all_results if r.get("status") == "fail"),
        },
        "results": all_results,
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"[workflow-batch] Done. Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
