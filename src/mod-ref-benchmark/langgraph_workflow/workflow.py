from __future__ import annotations

import argparse
import json
import sys
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


class WorkflowState(TypedDict, total=False):
    problem: str
    problem_path: str
    cr: str
    parser_json: str
    planner_json: str
    generated_model_path: str
    exec_ok: bool
    exec_error: str
    validator_status: str
    validator_output: Dict[str, Any]
    error_message: str
    loop_count: int
    max_loops: int
    model_name: str
    temperature: float


def parser_node(state: WorkflowState) -> WorkflowState:
    parser_output, parser_path = run_parser_agent(
        problem_path=state["problem_path"],
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
    )
    return {"parser_json": str(parser_path)}


def planner_node(state: WorkflowState) -> WorkflowState:
    planner_output, planner_path = run_planner_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        parser_json=state["parser_json"],
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
    )
    return {"planner_json": str(planner_path)}


def modifier_node(state: WorkflowState) -> WorkflowState:
    prev_code: Optional[str] = None
    if state.get("generated_model_path") and Path(state["generated_model_path"]).exists():
        prev_code = Path(state["generated_model_path"]).read_text()

    loop_count = state.get("loop_count", 0) + 1

    code, output_path = run_modifier_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        planner_json=state["planner_json"],
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
    }


def executor_node(state: WorkflowState) -> WorkflowState:
    try:
        _, _ = run_executor_agent(
            problem_path=state["problem_path"],
            cr_name=state["cr"],
            model_filename=Path(state["generated_model_path"]).name,
        )
        return {"exec_ok": True, "exec_error": None}
    except Exception as e:
        return {"exec_ok": False, "exec_error": str(e), "error_message": str(e)}


def validator_node(state: WorkflowState) -> WorkflowState:
    validator_output, _ = run_validator_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        generated_model_filename=Path(state["generated_model_path"]).name,
        model_name=state.get("model_name"),
        temperature=state.get("temperature", 0.0),
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


def route_after_executor(state: WorkflowState) -> str:
    if state.get("loop_count", 0) >= state.get("max_loops", 5):
        return "end"
    return "validator" if state.get("exec_ok") else "modifier"


def route_after_validator(state: WorkflowState) -> str:
    if state.get("loop_count", 0) >= state.get("max_loops", 5):
        return "end"
    return "end" if state.get("validator_status") == "pass" else "modifier"


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)
    graph.add_node("parser", parser_node)
    graph.add_node("planner", planner_node)
    graph.add_node("modifier", modifier_node)
    graph.add_node("executor", executor_node)
    graph.add_node("validator", validator_node)

    graph.add_edge(START, "parser")
    graph.add_edge("parser", "planner")
    graph.add_edge("planner", "modifier")
    graph.add_edge("modifier", "executor")
    graph.add_conditional_edges("executor", route_after_executor, {"modifier": "modifier", "validator": "validator"})
    graph.add_conditional_edges("validator", route_after_validator, {"modifier": "modifier", "end": END})
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
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
