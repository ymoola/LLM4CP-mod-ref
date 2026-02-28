from __future__ import annotations

import argparse
import json
import sys
import datetime
import importlib.util
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any

from langgraph.graph import StateGraph, START, END 

THIS_DIR = Path(__file__).resolve().parent
AGENTS_DIR = THIS_DIR.parent  # src/mod-ref-benchmark
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from parser_agent import run_parser_agent
from planner_agent import run_planner_agent
from modifier_agent import run_modifier_agent
from executor_agent import run_executor_agent
from validator_agent import run_validator_agent


def load_verify_func(unit_test_path: Path):
    """Dynamically load the verification function from a CR's unit_test.py file."""
    spec = importlib.util.spec_from_file_location("verify", unit_test_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_funcs = [getattr(module, f) for f in dir(module) if f.endswith("_verify_func")]
    if not verify_funcs:
        raise ValueError(f"No *_verify_func found in {unit_test_path}")
    return verify_funcs[0]


class WorkflowState(TypedDict, total=False):
    problem: str
    problem_path: str
    cr: str
    llm_config: Dict[str, Any]
    parser_json: str
    parser_output: Dict[str, Any]
    planner_json: str
    planner_output: Dict[str, Any]
    generated_model_path: str
    exec_ok: bool
    exec_error: str
    executor_output: Dict[str, Any]
    validator_status: str
    validator_output: Dict[str, Any]
    error_message: str
    loop_count: int
    exec_error_count: int
    validation_error_count: int
    max_exec_error_loops: int
    max_validation_error_loops: int
    unit_test_result: Dict[str, Any]
    unit_test_result_path: str
    termination_reason: str
    run_output_dir: str
    executor_timeout: Optional[int]


def _default_run_output_dir(problem_path: str, cr: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return Path(problem_path) / cr / "results" / timestamp


def _resolve_run_output_dir(state: WorkflowState) -> Path:
    run_output_dir = state.get("run_output_dir")
    if run_output_dir:
        out_dir = Path(run_output_dir)
    else:
        out_dir = _default_run_output_dir(state["problem_path"], state["cr"])
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _max_exec_error_loops(state: WorkflowState) -> int:
    if state.get("max_exec_error_loops") is not None:
        return int(state["max_exec_error_loops"])
    return 5


def _max_validation_error_loops(state: WorkflowState) -> int:
    if state.get("max_validation_error_loops") is not None:
        return int(state["max_validation_error_loops"])
    return 5


def _is_unit_test_pass(verify_result: Any) -> bool:
    if verify_result == "pass":
        return True
    if isinstance(verify_result, (list, tuple)) and verify_result and verify_result[0] == "pass":
        return True
    return False


def parser_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: parser | problem={state.get('problem_path')} cr={state.get('cr')}")
    parser_output, parser_path = run_parser_agent(
        problem_path=state["problem_path"],
        llm_config=state.get("llm_config"),
        write_output=False,
    )
    return {"parser_json": str(parser_path) if parser_path else None, "parser_output": parser_output}


def planner_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: planner | problem={state.get('problem_path')} cr={state.get('cr')}")
    planner_output, planner_path = run_planner_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        parser_json=state.get("parser_json"),
        parser_mapping=state.get("parser_output"),
        llm_config=state.get("llm_config"),
        output_path=False,
    )
    return {"planner_json": str(planner_path) if planner_path else None, "planner_output": planner_output}


def modifier_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: modifier | loop={state.get('loop_count',0)+1} | cr={state.get('cr')}")
    prev_code: Optional[str] = None
    if state.get("generated_model_path") and Path(state["generated_model_path"]).exists():
        prev_code = Path(state["generated_model_path"]).read_text()

    loop_count = state.get("loop_count", 0) + 1

    # Use a coding-optimized model only for the modifier step when using OpenAI.
    modifier_llm_config = dict(state.get("llm_config") or {})
    if modifier_llm_config.get("provider") == "openai":
        modifier_llm_config["model"] = "gpt-5.1-codex-max"

    code, output_path, _ = run_modifier_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        planner_json=state.get("planner_json"),
        planner_plan=state.get("planner_output"),
        llm_config=modifier_llm_config or state.get("llm_config"),
        previous_code=prev_code,
        error_message=state.get("error_message"),
    )
    return {
        "generated_model_path": str(output_path),
        "error_message": None,
        "exec_ok": None,
        "exec_error": None,
        "validator_status": None,
        "validator_output": None,
        "loop_count": loop_count,
        "executor_output": None,
        "parser_json": state.get("parser_json"),
        "planner_json": state.get("planner_json"),
    }


def executor_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: executor | cr={state.get('cr')}")
    timeout = state.get("executor_timeout")
    try:
        model_output, _ = run_executor_agent(
            problem_path=state["problem_path"],
            cr_name=state["cr"],
            model_filename=Path(state["generated_model_path"]).name,
            timeout=timeout,
            write_log=False,
        )
        return {
            "exec_ok": True,
            "exec_error": None,
            "executor_output": model_output,
        }
    except Exception as e:
        exec_error_count = int(state.get("exec_error_count", 0) or 0) + 1
        return {
            "exec_ok": False,
            "exec_error": str(e),
            "error_message": str(e),
            "exec_error_count": exec_error_count,
        }


def validator_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: validator | cr={state.get('cr')}")
    validator_output, _ = run_validator_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        generated_model_filename=Path(state["generated_model_path"]).name,
        llm_config=state.get("llm_config"),
        output_path=False,
    )
    status = validator_output.get("status", "needs_changes")
    feedback = None
    validation_error_count = int(state.get("validation_error_count", 0) or 0)
    if status != "pass":
        validation_error_count += 1
        issues = validator_output.get("issues", [])
        print("[workflow] Validator returned needs_changes. Issues:")
        print(json.dumps(issues, indent=2))
        if issues:
            parts = []
            for issue in issues:
                title = issue.get("title", "")
                desc = issue.get("description", "")
                suggestion = issue.get("suggestion", "")
                parts.append(f"{title}: {desc} | Suggestion: {suggestion}")
            feedback = "; ".join(parts)
        else:
            feedback = validator_output.get("summary", "Validator requested changes.")
    return {
        "validator_status": status,
        "validator_output": validator_output,
        "error_message": feedback,
        "validation_error_count": validation_error_count,
    }


def unit_test_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: unit_test | cr={state.get('cr')}")
    problem_dir = Path(state["problem_path"])
    cr_dir = problem_dir / state["cr"]
    unit_test_path = cr_dir / "unit_test.py"
    input_path = cr_dir / "input_data.json"

    timeout = state.get("executor_timeout")
    try:
        model_output, _ = run_executor_agent(
            problem_path=state["problem_path"],
            cr_name=state["cr"],
            model_filename=Path(state["generated_model_path"]).name,
            timeout=timeout,
            write_log=False,
        )
        input_data = json.loads(input_path.read_text())
        verify_func = load_verify_func(unit_test_path)
        result = verify_func(input_data, model_output)
        status = "pass" if _is_unit_test_pass(result) else "fail"
        final_result = {"status": status, "result": result, "model_output": model_output}
    except Exception as e:
        status = "fail"
        final_result = {"status": status, "error": str(e)}

    output_dir = _resolve_run_output_dir(state)
    result_path = output_dir / f"{problem_dir.name}_{state['cr']}_unit_test.json"
    result_path.write_text(json.dumps(final_result, indent=2))

    termination_reason = state.get("termination_reason")
    if (
        termination_reason is None
        and state.get("validator_status") != "pass"
        and int(state.get("validation_error_count", 0) or 0) >= _max_validation_error_loops(state)
    ):
        termination_reason = "max_validation_error_loops_reached_ran_unit_test"

    return {
        "unit_test_result": final_result,
        "unit_test_result_path": str(result_path),
        "termination_reason": termination_reason,
    }


def route_after_executor(state: WorkflowState) -> str:
    # Always validate if the model runs successfully.
    if state.get("exec_ok"):
        return "validator"
    if int(state.get("exec_error_count", 0) or 0) >= _max_exec_error_loops(state):
        return "finalize"
    return "modifier"


def route_after_validator(state: WorkflowState) -> str:
    if state.get("validator_status") == "pass":
        return "unit_test"
    if int(state.get("validation_error_count", 0) or 0) >= _max_validation_error_loops(state):
        if state.get("exec_ok"):
            return "unit_test"
        return "finalize"
    return "modifier"


def finalize_node(state: WorkflowState) -> WorkflowState:
    """Ensure final state explains why we stopped."""
    exec_ok = state.get("exec_ok")
    validator_status = state.get("validator_status")
    exec_error_count = int(state.get("exec_error_count", 0) or 0)
    validation_error_count = int(state.get("validation_error_count", 0) or 0)
    max_exec_error_loops = _max_exec_error_loops(state)
    max_validation_error_loops = _max_validation_error_loops(state)

    if exec_ok is False and exec_error_count >= max_exec_error_loops:
        reason = "max_exec_error_loops_reached"
    elif validator_status and validator_status != "pass" and validation_error_count >= max_validation_error_loops:
        reason = "max_validation_error_loops_reached"
    else:
        reason = "terminated"

    updates: WorkflowState = {"termination_reason": reason}

    # If we stop due to loop limits without an executor error, surface a non-null error string.
    if not state.get("exec_error") and reason in {"max_exec_error_loops_reached", "max_validation_error_loops_reached"}:
        updates["exec_error"] = f"Workflow stopped: {reason}"

    # If we terminate before validation ran, make it explicit in the final log.
    if state.get("validator_status") is None:
        updates["validator_status"] = "skipped"
        updates["validator_output"] = {
            "status": "needs_changes",
            "summary": "Validator skipped because workflow terminated before validation.",
            "issues": [],
            "notes_for_modifier": "",
        }

    print(f"[workflow] Terminating early: {reason}")
    return updates


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)
    graph.add_node("parser", parser_node)
    graph.add_node("planner", planner_node)
    graph.add_node("modifier", modifier_node)
    graph.add_node("executor", executor_node)
    graph.add_node("validator", validator_node)
    graph.add_node("unit_test", unit_test_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "parser")
    graph.add_edge("parser", "planner")
    graph.add_edge("planner", "modifier")
    graph.add_edge("modifier", "executor")
    graph.add_conditional_edges(
        "executor",
        route_after_executor,
        {"modifier": "modifier", "validator": "validator", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {"modifier": "modifier", "unit_test": "unit_test", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    graph.add_edge("unit_test", END)
    return graph.compile()


def build_llm_config(
    *,
    provider: str,
    model_name: str,
    reasoning_effort: str | None = None,
    max_output_tokens: int | None = None,
) -> Dict[str, Any]:
    if provider == "openai" and model_name == "gpt-oss:20b":
        model_name = "gpt-5-mini-2025-08-07"
    return {
        "provider": provider,
        "model": model_name,
        "reasoning_effort": reasoning_effort,
        "max_output_tokens": max_output_tokens,
    }


def run_workflow_once(
    *,
    problem_path: str,
    cr: str,
    llm_config: Dict[str, Any],
    max_exec_error_loops: int = 5,
    max_validation_error_loops: int = 5,
    executor_timeout: int = 30,
    run_output_dir: str | Path | None = None,
) -> tuple[WorkflowState, Dict[str, Any], Path]:
    graph = build_graph()

    if run_output_dir is None:
        out_dir = _default_run_output_dir(problem_path, cr)
    else:
        out_dir = Path(run_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timeout_value: int | None
    if executor_timeout and executor_timeout > 0:
        timeout_value = int(executor_timeout)
    else:
        timeout_value = None

    state: WorkflowState = {
        "problem": Path(problem_path).name,
        "problem_path": problem_path,
        "cr": cr,
        "loop_count": 0,
        "exec_error_count": 0,
        "validation_error_count": 0,
        "max_exec_error_loops": max_exec_error_loops,
        "max_validation_error_loops": max_validation_error_loops,
        "llm_config": llm_config,
        "run_output_dir": str(out_dir),
        "executor_timeout": timeout_value,
    }

    result = graph.invoke(state)

    run_log = {
        "problem": result.get("problem"),
        "cr": result.get("cr"),
        "llm_config": llm_config,
        "max_exec_error_loops": max_exec_error_loops,
        "max_validation_error_loops": max_validation_error_loops,
        "executor_timeout": timeout_value,
        "loop_count": result.get("loop_count"),
        "exec_error_count": result.get("exec_error_count"),
        "validation_error_count": result.get("validation_error_count"),
        "termination_reason": result.get("termination_reason"),
        "parser_output": result.get("parser_output"),
        "planner_output": result.get("planner_output"),
        "executor_output": result.get("executor_output"),
        "exec_error": result.get("exec_error"),
        "validator_output": result.get("validator_output"),
        "validator_status": result.get("validator_status"),
        "unit_test_result": result.get("unit_test_result"),
        "unit_test_result_path": result.get("unit_test_result_path"),
        "generated_model_path": result.get("generated_model_path"),
        "run_output_dir": str(out_dir),
    }
    log_path = out_dir / f"{result.get('problem')}_{result.get('cr')}_workflow_log.json"
    log_path.write_text(json.dumps(run_log, indent=2))

    return result, run_log, log_path


def main():
    parser = argparse.ArgumentParser(description="LangGraph workflow for ModRef agents.")
    parser.add_argument("--problem-path", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai"],
        default="openai",
        help="LLM provider to use for all LLM calls (default: openai).",
    )
    parser.add_argument(
        "--model-name",
        default="gpt-oss:20b",
        help="Model name to use for all LLM calls (default: gpt-oss:20b).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        help="Optional OpenAI reasoning effort (ignored by ollama).",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens for OpenAI Responses API (ignored by ollama).",
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
        help="Maximum number of validation-error retries before forcing unit test on current executable model.",
    )
    parser.add_argument(
        "--executor-timeout",
        type=int,
        default=30,
        help="Per execution timeout in seconds for generated models (0 disables timeout).",
    )

    args = parser.parse_args()

    llm_config = build_llm_config(
        provider=args.provider,
        model_name=args.model_name,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )

    result, run_log, log_path = run_workflow_once(
        problem_path=args.problem_path,
        cr=args.cr,
        llm_config=llm_config,
        max_exec_error_loops=args.max_exec_error_loops,
        max_validation_error_loops=args.max_validation_error_loops,
        executor_timeout=args.executor_timeout,
    )

    print(json.dumps(run_log, indent=2))
    print(f"Run log saved to {log_path}")


if __name__ == "__main__":
    main()
