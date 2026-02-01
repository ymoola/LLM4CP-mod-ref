from __future__ import annotations

import argparse
import json
import sys
import datetime
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, List

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
from og_workflow_simple.run_modref import load_verify_func


class WorkflowState(TypedDict, total=False):
    problem: str
    problem_path: str
    cr: str
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
    max_loops: int
    model_name: str
    temperature: float
    unit_test_result: Dict[str, Any]
    unit_test_result_path: str


def parser_node(state: WorkflowState) -> WorkflowState:
    parser_output, parser_path = run_parser_agent(
        problem_path=state["problem_path"],
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
        write_output=False,
    )
    return {"parser_json": str(parser_path) if parser_path else None, "parser_output": parser_output}


def planner_node(state: WorkflowState) -> WorkflowState:
    planner_output, planner_path = run_planner_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        parser_json=state.get("parser_json"),
        parser_mapping=state.get("parser_output"),
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
        output_path=False,
    )
    return {"planner_json": str(planner_path) if planner_path else None, "planner_output": planner_output}


def modifier_node(state: WorkflowState) -> WorkflowState:
    prev_code: Optional[str] = None
    if state.get("generated_model_path") and Path(state["generated_model_path"]).exists():
        prev_code = Path(state["generated_model_path"]).read_text()

    loop_count = state.get("loop_count", 0) + 1

    code, output_path, _ = run_modifier_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        planner_json=state.get("planner_json"),
        planner_plan=state.get("planner_output"),
        model_name=state.get("model_name"),
        previous_code=prev_code,
        error_message=state.get("error_message"),
        temperature=state.get("temperature", 0.0),
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
    try:
        model_output, _ = run_executor_agent(
            problem_path=state["problem_path"],
            cr_name=state["cr"],
            model_filename=Path(state["generated_model_path"]).name,
            write_log=False,
        )
        return {"exec_ok": True, "exec_error": None, "executor_output": model_output}
    except Exception as e:
        return {"exec_ok": False, "exec_error": str(e), "error_message": str(e)}


def validator_node(state: WorkflowState) -> WorkflowState:
    validator_output, _ = run_validator_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        generated_model_filename=Path(state["generated_model_path"]).name,
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
        output_path=False,
    )
    status = validator_output.get("status", "needs_changes")
    feedback = None
    if status != "pass":
        issues = validator_output.get("issues", [])
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
    }


def unit_test_node(state: WorkflowState) -> WorkflowState:
    problem_dir = Path(state["problem_path"])
    cr_dir = problem_dir / state["cr"]
    unit_test_path = cr_dir / "unit_test.py"
    input_path = cr_dir / "input_data.json"

    try:
        model_output, _ = run_executor_agent(
            problem_path=state["problem_path"],
            cr_name=state["cr"],
            model_filename=Path(state["generated_model_path"]).name,
            write_log=False,
        )
        input_data = json.loads(input_path.read_text())
        verify_func = load_verify_func(unit_test_path)
        result = verify_func(input_data, model_output)
        status = "pass"
        final_result = {"status": status, "result": result, "model_output": model_output}
    except Exception as e:
        status = "fail"
        final_result = {"status": status, "error": str(e)}

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_path = cr_dir / f"{problem_dir.name}_{state['cr']}_unit_test_{timestamp}.json"
    result_path.write_text(json.dumps(final_result, indent=2))

    return {
        "unit_test_result": final_result,
        "unit_test_result_path": str(result_path),
    }


def route_after_executor(state: WorkflowState) -> str:
    if state.get("loop_count", 0) >= state.get("max_loops", 5):
        return "end"
    return "validator" if state.get("exec_ok") else "modifier"


def route_after_validator(state: WorkflowState) -> str:
    if state.get("loop_count", 0) >= state.get("max_loops", 5):
        return "end"
    return "unit_test" if state.get("validator_status") == "pass" else "modifier"


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)
    graph.add_node("parser", parser_node)
    graph.add_node("planner", planner_node)
    graph.add_node("modifier", modifier_node)
    graph.add_node("executor", executor_node)
    graph.add_node("validator", validator_node)
    graph.add_node("unit_test", unit_test_node)

    graph.add_edge(START, "parser")
    graph.add_edge("parser", "planner")
    graph.add_edge("planner", "modifier")
    graph.add_edge("modifier", "executor")
    graph.add_conditional_edges("executor", route_after_executor, {"modifier": "modifier", "validator": "validator"})
    graph.add_conditional_edges("validator", route_after_validator, {"modifier": "modifier", "unit_test": "unit_test"})
    graph.add_edge("unit_test", END)
    return graph.compile()


def main():
    parser = argparse.ArgumentParser(description="LangGraph workflow for ModRef agents.")
    parser.add_argument("--problem-path", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument(
        "--model-name",
        default="gpt-oss:20b",
        help="Ollama model name to use for all LLM calls.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for LLM calls.",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=5,
        help="Maximum modifier/executor/validator loops before stopping.",
    )

    args = parser.parse_args()

    graph = build_graph()

    state: WorkflowState = {
        "problem": Path(args.problem_path).name,
        "problem_path": args.problem_path,
        "cr": args.cr,
        "loop_count": 0,
        "max_loops": args.max_loops,
        "model_name": args.model_name,
        "temperature": args.temperature,
    }

    result = graph.invoke(state)
    # Aggregate run log (single file)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    cr_dir = Path(args.problem_path) / args.cr
    run_log = {
        "problem": result.get("problem"),
        "cr": result.get("cr"),
        "model_name": args.model_name,
        "temperature": args.temperature,
        "max_loops": args.max_loops,
        "loop_count": result.get("loop_count"),
        "parser_output": result.get("parser_output"),
        "planner_output": result.get("planner_output"),
        "executor_output": result.get("executor_output"),
        "exec_error": result.get("exec_error"),
        "validator_output": result.get("validator_output"),
        "validator_status": result.get("validator_status"),
        "unit_test_result": result.get("unit_test_result"),
        "unit_test_result_path": result.get("unit_test_result_path"),
        "generated_model_path": result.get("generated_model_path"),
    }
    log_path = cr_dir / f"{result.get('problem')}_{result.get('cr')}_workflow_log_{timestamp}.json"
    log_path.write_text(json.dumps(run_log, indent=2))

    print(json.dumps(run_log, indent=2))
    print(f"Run log saved to {log_path}")


if __name__ == "__main__":
    main()
