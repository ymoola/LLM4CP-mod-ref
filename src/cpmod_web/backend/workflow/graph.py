from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .prompts import (
    build_clarification_assessor_prompt,
    build_modifier_prompt,
    build_parser_prompt,
    build_planner_prompt,
    build_planner_validator_prompt,
    build_validator_prompt,
    number_code_lines,
)
from .schemas import (
    clarification_assessor_schema,
    parser_schema,
    planner_schema,
    planner_validator_schema,
    validator_schema,
)
from .state import WorkflowState


def build_graph(runtime: Any, *, start_node: str = 'parsing'):
    graph = StateGraph(WorkflowState)

    def parsing_node(state: WorkflowState) -> WorkflowState:
        runtime.log_stage('parsing', 'started', attempt=1)
        if runtime.model_package.get('parser_output'):
            parser_output = runtime.model_package['parser_output']
        elif state.get('parser_output'):
            parser_output = state['parser_output']
        else:
            parser_output = runtime.llm.generate_json(
                prompt=build_parser_prompt(
                    problem_description=state['problem_description'],
                    numbered_model=number_code_lines(state['base_model_code']),
                    metadata=state['metadata'],
                    schema=parser_schema(),
                ),
                schema=parser_schema(),
                schema_name='parser_output',
                system='Map the uploaded problem description to the CPMpy model.',
            )
            runtime.cache_parser_output(parser_output)
        runtime.log_stage('parsing', 'succeeded', attempt=1)
        return {'parser_output': parser_output}

    def clarification_node(state: WorkflowState) -> WorkflowState:
        attempt = len(state.get('clarification_transcript', [])) + 1
        runtime.log_stage('clarification_assessment', 'started', attempt=attempt)
        output = runtime.llm.generate_json(
            prompt=build_clarification_assessor_prompt(
                problem_description=state['problem_description'],
                change_request=state['change_request'],
                parser_output=state['parser_output'],
                metadata=state['metadata'],
                schema=clarification_assessor_schema(),
                input_data=state['input_data'],
                runtime_input_source=state.get('runtime_input_source'),
                runtime_input_filename=state.get('runtime_input_filename'),
                transcript=state.get('clarification_transcript', []),
            ),
            schema=clarification_assessor_schema(),
            schema_name='clarification_assessment',
            system='Decide whether the uploaded change request needs clarification before planning.',
        )
        runtime.log_stage('clarification_assessment', 'succeeded', attempt=attempt)
        return {
            'clarification_status': output['status'],
            'clarification_questions': output['questions'],
            'clarified_request_summary': output['clarified_request_summary'],
        }

    def pause_node(state: WorkflowState) -> WorkflowState:
        questions = state.get('clarification_questions', [])
        runtime.persist_pause(state=state, questions=questions)
        runtime.log_stage(
            'clarification_waiting',
            'waiting',
            attempt=len(state.get('clarification_transcript', [])) + 1,
            message='Awaiting clarification from user.',
            payload={'questions': questions},
        )
        return {'final_status': 'awaiting_clarification'}

    def planner_node(state: WorkflowState) -> WorkflowState:
        attempt = int(state.get('planner_validation_attempts', 0) or 0) + 1
        runtime.log_stage('planning', 'started', attempt=attempt)
        output = runtime.llm.generate_json(
            prompt=build_planner_prompt(
                problem_description=state['problem_description'],
                change_request=state['change_request'],
                metadata=state['metadata'],
                parser_output=state['parser_output'],
                numbered_model=number_code_lines(state['base_model_code']),
                schema=planner_schema(),
                input_data=state['input_data'],
                runtime_input_source=state.get('runtime_input_source'),
                runtime_input_filename=state.get('runtime_input_filename'),
                transcript=state.get('clarification_transcript', []),
                clarified_summary=state.get('clarified_request_summary'),
                previous_plan=state.get('planner_output'),
                feedback=state.get('planner_feedback'),
            ),
            schema=planner_schema(),
            schema_name='planner_output',
            system='Produce a precise edit plan for modifying the CPMpy model.',
        )
        runtime.log_stage('planning', 'succeeded', attempt=attempt)
        return {'planner_output': output}

    def plan_validator_node(state: WorkflowState) -> WorkflowState:
        attempt = int(state.get('planner_validation_attempts', 0) or 0) + 1
        runtime.log_stage('plan_validation', 'started', attempt=attempt)
        output = runtime.llm.generate_json(
            prompt=build_planner_validator_prompt(
                problem_description=state['problem_description'],
                change_request=state['change_request'],
                metadata=state['metadata'],
                parser_output=state['parser_output'],
                planner_output=state['planner_output'],
                numbered_model=number_code_lines(state['base_model_code']),
                schema=planner_validator_schema(),
                input_data=state['input_data'],
                runtime_input_source=state.get('runtime_input_source'),
                runtime_input_filename=state.get('runtime_input_filename'),
                transcript=state.get('clarification_transcript', []),
                clarified_summary=state.get('clarified_request_summary'),
            ),
            schema=planner_validator_schema(),
            schema_name='planner_validator_output',
            system='Review the planner output for correctness and preservation risks.',
        )
        if output['status'] == 'pass':
            runtime.log_stage('plan_validation', 'succeeded', attempt=attempt)
            return {
                'planner_validator_output': output,
                'planner_validator_status': 'pass',
                'planner_feedback': '',
            }
        feedback = output.get('notes_for_planner') or output.get('summary', 'Planner validation requested changes.')
        runtime.log_stage('plan_validation', 'failed', attempt=attempt, message=feedback, failure_type='planner_rejected')
        return {
            'planner_validator_output': output,
            'planner_validator_status': 'needs_changes',
            'planner_validation_attempts': attempt,
            'planner_feedback': feedback,
        }

    def modifier_node(state: WorkflowState) -> WorkflowState:
        attempt = int(state.get('execution_attempts', 0) or 0) + 1
        runtime.log_stage('modification', 'started', attempt=attempt)
        code = runtime.llm.generate_text(
            prompt=build_modifier_prompt(
                problem_description=state['problem_description'],
                base_model_code=state['base_model_code'],
                numbered_model=number_code_lines(state['base_model_code']),
                change_request=state['change_request'],
                metadata=state['metadata'],
                plan=state['planner_output'],
                input_data=state['input_data'],
                runtime_input_source=state.get('runtime_input_source'),
                runtime_input_filename=state.get('runtime_input_filename'),
                clarification_transcript=state.get('clarification_transcript', []),
                clarified_summary=state.get('clarified_request_summary'),
                previous_code=state.get('generated_code'),
                feedback=state.get('execution_error') or state.get('validator_feedback') or state.get('planner_feedback'),
            ),
            system='Return only valid Python code for the modified CPMpy model.',
        )
        artifact_path = runtime.save_generated_model(code=code, attempt=attempt)
        runtime.log_stage('modification', 'succeeded', attempt=attempt)
        return {'generated_code': code, 'generated_model_artifact_path': artifact_path}

    async def execution_node(state: WorkflowState) -> WorkflowState:
        attempt = int(state.get('execution_attempts', 0) or 0) + 1
        runtime.log_stage('execution', 'started', attempt=attempt)
        result = await runtime.executor.execute_model(
            code=state['generated_code'],
            input_data=state['input_data'],
            metadata=state.get('metadata'),
        )
        runtime.save_execution_log(result=result, attempt=attempt)
        if result.passed:
            runtime.log_stage('execution', 'succeeded', attempt=attempt, message='Generated model executed successfully.')
            return {
                'execution_ok': True,
                'execution_output': result.model_dump(),
                'execution_error': '',
                'execution_attempts': attempt,
            }
        runtime.log_stage(
            'execution',
            'failed',
            attempt=attempt,
            message=result.stderr or result.stdout or 'Execution failed.',
            failure_type=result.error_type.value if result.error_type else 'runtime_error',
        )
        return {
            'execution_ok': False,
            'execution_output': result.model_dump(),
            'execution_error': result.stderr or result.stdout or 'Execution failed.',
            'execution_attempts': attempt,
        }

    def semantic_validator_node(state: WorkflowState) -> WorkflowState:
        attempt = int(state.get('validator_attempts', 0) or 0) + 1
        runtime.log_stage('semantic_validation', 'started', attempt=attempt)
        output = runtime.llm.generate_json(
            prompt=build_validator_prompt(
                problem_description=state['problem_description'],
                base_model_code=state['base_model_code'],
                generated_model_code=state['generated_code'],
                change_request=state['change_request'],
                metadata=state['metadata'],
                schema=validator_schema(),
                input_data=state['input_data'],
                runtime_input_source=state.get('runtime_input_source'),
                runtime_input_filename=state.get('runtime_input_filename'),
                clarification_transcript=state.get('clarification_transcript', []),
                clarified_summary=state.get('clarified_request_summary'),
            ),
            schema=validator_schema(),
            schema_name='validator_output',
            system='Review the generated model for semantic correctness and preservation of expected behavior.',
        )
        runtime.save_validator_report(output=output, attempt=attempt)
        if output['status'] == 'pass':
            runtime.log_stage('semantic_validation', 'succeeded', attempt=attempt)
            return {
                'validator_output': output,
                'validator_status': 'pass',
                'validator_attempts': attempt,
                'validator_feedback': '',
                'change_summary': output.get('change_summary', ''),
                'invariants': output.get('invariants', {}),
            }
        feedback = output.get('notes_for_modifier') or output.get('summary', 'Semantic validation requested changes.')
        runtime.log_stage('semantic_validation', 'failed', attempt=attempt, message=feedback, failure_type='validation_rejected')
        return {
            'validator_output': output,
            'validator_status': 'needs_changes',
            'validator_attempts': attempt,
            'validator_feedback': feedback,
            'change_summary': output.get('change_summary', ''),
            'invariants': output.get('invariants', {}),
        }

    def finalize_node(state: WorkflowState) -> WorkflowState:
        final_status = 'failed'
        failure_type = state.get('failure_type') or 'runtime_error'
        if state.get('execution_ok') and state.get('validator_status') == 'pass':
            final_status = 'completed'
            failure_type = ''
        elif state.get('execution_ok'):
            final_status = 'needs_review'
            failure_type = 'validation_rejected'
        runtime.finalize_run(state=state, final_status=final_status, failure_type=failure_type)
        runtime.log_stage('finalize', 'succeeded', attempt=1, message=f'Run finished with status {final_status}.')
        return {'final_status': final_status, 'failure_type': failure_type}

    graph.add_node('parsing', parsing_node)
    graph.add_node('clarification_assessment', clarification_node)
    graph.add_node('pause_for_clarification', pause_node)
    graph.add_node('planning', planner_node)
    graph.add_node('plan_validation', plan_validator_node)
    graph.add_node('modification', modifier_node)
    graph.add_node('execution', execution_node)
    graph.add_node('semantic_validation', semantic_validator_node)
    graph.add_node('finalize', finalize_node)

    graph.add_edge(START, start_node)
    if start_node == 'parsing':
        graph.add_edge('parsing', 'clarification_assessment')
        graph.add_conditional_edges(
            'clarification_assessment',
            lambda state: 'pause_for_clarification' if state.get('clarification_status') == 'needs_clarification' and not state.get('clarification_answers') else 'planning',
            {'pause_for_clarification': 'pause_for_clarification', 'planning': 'planning'},
        )
        graph.add_edge('pause_for_clarification', END)
    graph.add_edge('planning', 'plan_validation')
    graph.add_conditional_edges(
        'plan_validation',
        lambda state: 'modification' if state.get('planner_validator_status') == 'pass' or int(state.get('planner_validation_attempts', 0) or 0) >= int(state.get('max_planner_validation_loops', 5) or 5) else 'planning',
        {'planning': 'planning', 'modification': 'modification'},
    )
    graph.add_edge('modification', 'execution')
    graph.add_conditional_edges(
        'execution',
        lambda state: 'semantic_validation' if state.get('execution_ok') else ('finalize' if int(state.get('execution_attempts', 0) or 0) >= int(state.get('max_execution_loops', 5) or 5) else 'modification'),
        {'semantic_validation': 'semantic_validation', 'modification': 'modification', 'finalize': 'finalize'},
    )
    graph.add_conditional_edges(
        'semantic_validation',
        lambda state: 'finalize' if state.get('validator_status') == 'pass' or int(state.get('validator_attempts', 0) or 0) >= int(state.get('max_validator_loops', 5) or 5) else 'modification',
        {'modification': 'modification', 'finalize': 'finalize'},
    )
    graph.add_edge('finalize', END)
    return graph.compile()
