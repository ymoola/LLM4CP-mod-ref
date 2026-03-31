from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

THIS_DIR = Path(__file__).resolve().parent
AGENTS_DIR = THIS_DIR.parent  # src/mod-ref-benchmark
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from llm_client import DEFAULT_OPENAI_MODEL, DEFAULT_OPENAI_REASONING_EFFORT
from agents.clarification_assessor_agent import run_clarification_assessor_agent
from agents.executor_agent import run_executor_agent
from agents.modifier_agent import run_modifier_agent
from agents.parser_agent import run_parser_agent
from agents.planner_agent import run_planner_agent
from agents.planner_validator_agent import run_planner_validator_agent
from agents.validator_agent import run_validator_agent


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
    clarification_status: str
    clarification_output: Dict[str, Any]
    clarification_transcript: list[dict[str, Any]]
    clarified_cr_summary: str
    clarification_turn_count: int
    max_clarification_turns: int
    planner_json: str
    planner_output: Dict[str, Any]
    planner_validator_status: str
    planner_validator_output: Dict[str, Any]
    planner_feedback: str
    generated_model_path: str
    exec_ok: bool
    exec_error: str
    executor_output: Dict[str, Any]
    validator_status: str
    validator_output: Dict[str, Any]
    error_message: str
    loop_count: int
    planner_validation_error_count: int
    exec_error_count: int
    validation_error_count: int
    max_planner_validation_error_loops: int
    max_exec_error_loops: int
    max_validation_error_loops: int
    unit_test_result: Dict[str, Any]
    unit_test_result_path: str
    termination_reason: str
    run_output_dir: str
    executor_timeout: Optional[int]
    hitl_enabled: bool
    thread_id: str


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


def _max_planner_validation_error_loops(state: WorkflowState) -> int:
    if state.get("max_planner_validation_error_loops") is not None:
        return int(state["max_planner_validation_error_loops"])
    return 5


def _max_clarification_turns(state: WorkflowState) -> int:
    if state.get("max_clarification_turns") is not None:
        return int(state["max_clarification_turns"])
    return 2


def _is_unit_test_pass(verify_result: Any) -> bool:
    if verify_result == "pass":
        return True
    if isinstance(verify_result, (list, tuple)) and verify_result and verify_result[0] == "pass":
        return True
    return False


def _build_graph_config(thread_id: str | None) -> dict[str, Any] | None:
    if not thread_id:
        return None
    return {"configurable": {"thread_id": thread_id}}


def _interrupt_payload(result: Dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    if hasattr(first, "value"):
        return first.value
    if isinstance(first, dict):
        value = first.get("value")
        if isinstance(value, dict):
            return value
    if isinstance(first, dict):
        return first
    return None


def _prompt_for_clarification_answers(
    payload: dict[str, Any],
    *,
    input_func: Callable[[str], str],
) -> dict[str, list[str]]:
    questions = payload.get("questions") or []
    if not isinstance(questions, list):
        raise ValueError("Interrupt payload questions must be a list.")

    print(
        f"[workflow] Clarification needed for {payload.get('problem')}/{payload.get('cr')} "
        f"(turn {payload.get('turn')})."
    )
    reason = (payload.get("reason") or "").strip()
    if reason:
        print(f"[workflow] Reason: {reason}")

    transcript = payload.get("transcript_so_far") or []
    if transcript:
        print("[workflow] Previous clarification transcript:")
        print(json.dumps(transcript, indent=2))

    answers: list[str] = []
    for idx, question in enumerate(questions, start=1):
        answer = input_func(f"[workflow] Clarification {idx}/{len(questions)}: {question}\n> ")
        answers.append(answer)

    if len(answers) != len(questions):
        raise ValueError(
            f"Expected {len(questions)} clarification answers, received {len(answers)}."
        )
    return {"answers": answers}


def _invoke_with_optional_hitl(
    graph: Any,
    state: WorkflowState,
    *,
    hitl_enabled: bool,
    thread_id: str | None,
    human_input_func: Callable[[str], str],
) -> WorkflowState:
    config = _build_graph_config(thread_id)
    current_input: Any = state

    while True:
        if config is None:
            result = graph.invoke(current_input)
        else:
            result = graph.invoke(current_input, config=config)

        payload = _interrupt_payload(result)
        if payload is None:
            return result

        if not hitl_enabled:
            raise RuntimeError("Workflow requested human clarification while HITL is disabled.")
        if payload.get("kind") != "cr_clarification":
            raise RuntimeError(f"Unsupported interrupt payload: {payload}")

        resume_payload = _prompt_for_clarification_answers(payload, input_func=human_input_func)
        current_input = Command(resume=resume_payload)


def parser_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: parser | problem={state.get('problem_path')} cr={state.get('cr')}")
    parser_output, parser_path = run_parser_agent(
        problem_path=state["problem_path"],
        llm_config=state.get("llm_config"),
        write_output=False,
    )
    return {"parser_json": str(parser_path) if parser_path else None, "parser_output": parser_output}


def clarification_assessor_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: clarification_assessor | cr={state.get('cr')}")
    clarification_output, _ = run_clarification_assessor_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        parser_json=state.get("parser_json"),
        parser_mapping=state.get("parser_output"),
        clarification_transcript=state.get("clarification_transcript") or [],
        llm_config=state.get("llm_config"),
        output_path=False,
    )
    status = clarification_output.get("status", "needs_clarification")
    questions = clarification_output.get("questions") or []
    if status == "needs_clarification" and not questions:
        questions = ["Please clarify the parts of the change request that are still ambiguous."]
        clarification_output["questions"] = questions
    clarified_cr_summary = clarification_output.get("clarified_cr_summary", "")
    if status == "proceed" and not clarified_cr_summary:
        clarified_cr_summary = clarification_output.get("reason", "")
    return {
        "clarification_status": status,
        "clarification_output": clarification_output,
        "clarified_cr_summary": clarified_cr_summary if status == "proceed" else "",
    }


def human_clarification_node(state: WorkflowState) -> WorkflowState:
    turn = int(state.get("clarification_turn_count", 0) or 0) + 1
    clarification_output = state.get("clarification_output") or {}
    questions = clarification_output.get("questions") or []
    transcript = list(state.get("clarification_transcript") or [])

    answers_payload = interrupt(
        {
            "kind": "cr_clarification",
            "problem": state.get("problem"),
            "cr": state.get("cr"),
            "turn": turn,
            "reason": clarification_output.get("reason", ""),
            "questions": questions,
            "transcript_so_far": transcript,
        }
    )

    answers = []
    if isinstance(answers_payload, dict):
        answers = answers_payload.get("answers") or []
    transcript.append(
        {
            "turn": turn,
            "questions": questions,
            "answers": ["" if answer is None else str(answer) for answer in answers],
        }
    )
    return {
        "clarification_transcript": transcript,
        "clarification_turn_count": turn,
    }


def planner_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: planner | problem={state.get('problem_path')} cr={state.get('cr')}")
    planner_output, planner_path = run_planner_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        parser_json=state.get("parser_json"),
        parser_mapping=state.get("parser_output"),
        previous_plan=state.get("planner_output"),
        feedback=state.get("planner_feedback"),
        clarification_transcript=state.get("clarification_transcript") or [],
        clarified_cr_summary=state.get("clarified_cr_summary"),
        llm_config=state.get("llm_config"),
        output_path=False,
    )
    return {
        "planner_json": str(planner_path) if planner_path else None,
        "planner_output": planner_output,
        "planner_validator_status": None,
        "planner_validator_output": None,
        "planner_feedback": None,
    }


def planner_validator_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: planner_validator | cr={state.get('cr')}")
    validator_output, _ = run_planner_validator_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        planner_output=state.get("planner_output") or {},
        parser_mapping=state.get("parser_output") or {},
        clarification_transcript=state.get("clarification_transcript") or [],
        clarified_cr_summary=state.get("clarified_cr_summary"),
        llm_config=state.get("llm_config"),
        output_path=False,
    )
    status = validator_output.get("status", "needs_changes")
    feedback = None
    planner_validation_error_count = int(state.get("planner_validation_error_count", 0) or 0)
    if status != "pass":
        planner_validation_error_count += 1
        issues = validator_output.get("issues", [])
        print("[workflow] Planner validator returned needs_changes. Issues:")
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
            feedback = validator_output.get("notes_for_planner") or validator_output.get(
                "summary", "Planner validator requested changes."
            )
    return {
        "planner_validator_status": status,
        "planner_validator_output": validator_output,
        "planner_feedback": feedback,
        "planner_validation_error_count": planner_validation_error_count,
    }


def modifier_node(state: WorkflowState) -> WorkflowState:
    print(f"[workflow] Stage: modifier | loop={state.get('loop_count', 0) + 1} | cr={state.get('cr')}")
    prev_code: Optional[str] = None
    if state.get("generated_model_path") and Path(state["generated_model_path"]).exists():
        prev_code = Path(state["generated_model_path"]).read_text()

    loop_count = state.get("loop_count", 0) + 1

    code, output_path, _ = run_modifier_agent(
        problem_path=state["problem_path"],
        cr_name=state["cr"],
        planner_json=state.get("planner_json"),
        planner_plan=state.get("planner_output"),
        clarification_transcript=state.get("clarification_transcript") or [],
        clarified_cr_summary=state.get("clarified_cr_summary"),
        llm_config=state.get("llm_config"),
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
        clarification_transcript=state.get("clarification_transcript") or [],
        clarified_cr_summary=state.get("clarified_cr_summary"),
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


def route_after_parser(state: WorkflowState) -> str:
    if state.get("hitl_enabled"):
        return "clarification_assessor"
    return "planner"


def route_after_clarification_assessor(state: WorkflowState) -> str:
    if state.get("clarification_status") == "proceed":
        return "planner"
    if int(state.get("clarification_turn_count", 0) or 0) >= _max_clarification_turns(state):
        return "finalize"
    return "human_clarification"


def route_after_executor(state: WorkflowState) -> str:
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


def route_after_planner_validator(state: WorkflowState) -> str:
    if state.get("planner_validator_status") == "pass":
        return "modifier"
    if int(state.get("planner_validation_error_count", 0) or 0) >= _max_planner_validation_error_loops(state):
        return "finalize"
    return "planner"


def finalize_node(state: WorkflowState) -> WorkflowState:
    """Ensure final state explains why we stopped."""
    clarification_status = state.get("clarification_status")
    clarification_turn_count = int(state.get("clarification_turn_count", 0) or 0)
    exec_ok = state.get("exec_ok")
    planner_validator_status = state.get("planner_validator_status")
    validator_status = state.get("validator_status")
    planner_validation_error_count = int(state.get("planner_validation_error_count", 0) or 0)
    exec_error_count = int(state.get("exec_error_count", 0) or 0)
    validation_error_count = int(state.get("validation_error_count", 0) or 0)
    max_clarification_turns = _max_clarification_turns(state)
    max_planner_validation_error_loops = _max_planner_validation_error_loops(state)
    max_exec_error_loops = _max_exec_error_loops(state)
    max_validation_error_loops = _max_validation_error_loops(state)

    if clarification_status == "needs_clarification" and clarification_turn_count >= max_clarification_turns:
        reason = "max_clarification_turns_reached"
    elif (
        planner_validator_status
        and planner_validator_status != "pass"
        and planner_validation_error_count >= max_planner_validation_error_loops
    ):
        reason = "max_planner_validation_error_loops_reached"
    elif exec_ok is False and exec_error_count >= max_exec_error_loops:
        reason = "max_exec_error_loops_reached"
    elif validator_status and validator_status != "pass" and validation_error_count >= max_validation_error_loops:
        reason = "max_validation_error_loops_reached"
    else:
        reason = "terminated"

    updates: WorkflowState = {"termination_reason": reason}

    if not state.get("exec_error") and reason in {"max_exec_error_loops_reached", "max_validation_error_loops_reached"}:
        updates["exec_error"] = f"Workflow stopped: {reason}"

    if state.get("planner_validator_status") is None:
        updates["planner_validator_status"] = "skipped"
        updates["planner_validator_output"] = {
            "status": "needs_changes",
            "summary": "Planner validator skipped because workflow terminated before planner validation completed.",
            "issues": [],
            "notes_for_planner": "",
        }

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


def build_graph(*, hitl_enabled: bool = False, checkpointer: Any | None = None):
    graph = StateGraph(WorkflowState)
    graph.add_node("parser", parser_node)
    graph.add_node("clarification_assessor", clarification_assessor_node)
    graph.add_node("human_clarification", human_clarification_node)
    graph.add_node("planner", planner_node)
    graph.add_node("planner_validator", planner_validator_node)
    graph.add_node("modifier", modifier_node)
    graph.add_node("executor", executor_node)
    graph.add_node("validator", validator_node)
    graph.add_node("unit_test", unit_test_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "parser")
    graph.add_conditional_edges(
        "parser",
        route_after_parser,
        {"clarification_assessor": "clarification_assessor", "planner": "planner"},
    )
    graph.add_conditional_edges(
        "clarification_assessor",
        route_after_clarification_assessor,
        {
            "planner": "planner",
            "human_clarification": "human_clarification",
            "finalize": "finalize",
        },
    )
    graph.add_edge("human_clarification", "clarification_assessor")
    graph.add_edge("planner", "planner_validator")
    graph.add_conditional_edges(
        "planner_validator",
        route_after_planner_validator,
        {"planner": "planner", "modifier": "modifier", "finalize": "finalize"},
    )
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

    effective_checkpointer = checkpointer
    if effective_checkpointer is None and hitl_enabled:
        effective_checkpointer = InMemorySaver()

    compile_kwargs: dict[str, Any] = {}
    if effective_checkpointer is not None:
        compile_kwargs["checkpointer"] = effective_checkpointer
    return graph.compile(**compile_kwargs)


def build_llm_config(
    *,
    provider: str,
    model_name: str,
    reasoning_effort: str | None = None,
    max_output_tokens: int | None = None,
) -> Dict[str, Any]:
    if provider == "openai" and model_name == "gpt-oss:20b":
        model_name = DEFAULT_OPENAI_MODEL
    if provider == "openai" and reasoning_effort is None:
        reasoning_effort = DEFAULT_OPENAI_REASONING_EFFORT
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
    max_planner_validation_error_loops: int = 5,
    max_exec_error_loops: int = 5,
    max_validation_error_loops: int = 5,
    executor_timeout: int = 30,
    run_output_dir: str | Path | None = None,
    hitl_enabled: bool = False,
    max_clarification_turns: int = 2,
    thread_id: str | None = None,
    checkpointer: Any | None = None,
    human_input_func: Callable[[str], str] | None = None,
) -> tuple[WorkflowState, Dict[str, Any], Path]:
    graph = build_graph(hitl_enabled=hitl_enabled, checkpointer=checkpointer)

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

    resolved_thread_id = thread_id or (f"workflow-{uuid.uuid4()}" if hitl_enabled else "")
    input_func = human_input_func or input

    state: WorkflowState = {
        "problem": Path(problem_path).name,
        "problem_path": problem_path,
        "cr": cr,
        "loop_count": 0,
        "planner_validation_error_count": 0,
        "exec_error_count": 0,
        "validation_error_count": 0,
        "max_planner_validation_error_loops": max_planner_validation_error_loops,
        "max_exec_error_loops": max_exec_error_loops,
        "max_validation_error_loops": max_validation_error_loops,
        "max_clarification_turns": max_clarification_turns,
        "clarification_turn_count": 0,
        "clarification_transcript": [],
        "clarified_cr_summary": "",
        "llm_config": llm_config,
        "run_output_dir": str(out_dir),
        "executor_timeout": timeout_value,
        "hitl_enabled": hitl_enabled,
        "thread_id": resolved_thread_id,
    }

    result = _invoke_with_optional_hitl(
        graph,
        state,
        hitl_enabled=hitl_enabled,
        thread_id=resolved_thread_id or None,
        human_input_func=input_func,
    )

    run_log = {
        "problem": result.get("problem"),
        "cr": result.get("cr"),
        "llm_config": llm_config,
        "hitl_enabled": hitl_enabled,
        "thread_id": resolved_thread_id or None,
        "max_clarification_turns": max_clarification_turns,
        "max_planner_validation_error_loops": max_planner_validation_error_loops,
        "max_exec_error_loops": max_exec_error_loops,
        "max_validation_error_loops": max_validation_error_loops,
        "executor_timeout": timeout_value,
        "loop_count": result.get("loop_count"),
        "clarification_turn_count": result.get("clarification_turn_count"),
        "planner_validation_error_count": result.get("planner_validation_error_count"),
        "exec_error_count": result.get("exec_error_count"),
        "validation_error_count": result.get("validation_error_count"),
        "termination_reason": result.get("termination_reason"),
        "parser_output": result.get("parser_output"),
        "clarification_status": result.get("clarification_status"),
        "clarification_output": result.get("clarification_output"),
        "clarification_transcript": result.get("clarification_transcript"),
        "clarified_cr_summary": result.get("clarified_cr_summary"),
        "planner_output": result.get("planner_output"),
        "planner_validator_output": result.get("planner_validator_output"),
        "planner_validator_status": result.get("planner_validator_status"),
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
        default=DEFAULT_OPENAI_MODEL,
        help=f"Model name to use for all LLM calls (default: {DEFAULT_OPENAI_MODEL}).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        default=DEFAULT_OPENAI_REASONING_EFFORT,
        help=f"OpenAI reasoning effort (default: {DEFAULT_OPENAI_REASONING_EFFORT}; ignored by ollama).",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional max output tokens for OpenAI Responses API (ignored by ollama).",
    )
    parser.add_argument(
        "--enable-hitl",
        action="store_true",
        help="Enable optional human-in-the-loop clarification after parsing and before planning.",
    )
    parser.add_argument(
        "--max-clarification-turns",
        type=int,
        default=2,
        help="Maximum number of clarification rounds before failing early (default: 2).",
    )
    parser.add_argument(
        "--thread-id",
        help="Optional LangGraph thread ID to use for HITL sessions.",
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
        max_planner_validation_error_loops=args.max_planner_validation_error_loops,
        max_exec_error_loops=args.max_exec_error_loops,
        max_validation_error_loops=args.max_validation_error_loops,
        executor_timeout=args.executor_timeout,
        hitl_enabled=args.enable_hitl,
        max_clarification_turns=args.max_clarification_turns,
        thread_id=args.thread_id,
    )

    print(json.dumps(run_log, indent=2))
    print(f"Run log saved to {log_path}")


if __name__ == "__main__":
    main()
