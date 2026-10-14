from .telemetry import observe
"""LangGraph state, checkpointing, and human approval."""
from typing import TypedDict
from uuid import uuid4
from threading import RLock
from langgraph.graph import StateGraph, START, END
from .persistence import DurableGraph
from langgraph.types import interrupt, Command
from .agent import generate
from .agents.test_design_agent import design, criteria_for
from .agents.test_data_agent import generate_data
from .services.coverage_evaluator import evaluate_coverage

class QAState(TypedDict, total=False):
    requirement: str
    analysis: dict
    mode: str
    decision: str
    status: str
    phase: str
    criteria: list[dict]
    test_cases: list[dict]
    test_data: list[dict]
    metrics: dict
    errors: list[dict]

@observe('analyze_node')
def analyze_node(state: QAState):
    try:
        result, mode = generate(state['requirement'])
        return {'analysis': result.model_dump(), 'mode': mode, 'status': 'awaiting_approval', 'phase': 'requirements_review'}
    except Exception as exc:
        return {'analysis': None, 'mode': None, 'status': 'failed', 'phase': 'failed',
                'errors': [{'agent': 'requirements', 'kind': type(exc).__name__,
                            'message': 'Requirements Agent failed validation or provider execution. No analysis is available.'}]}

def review_node(state: QAState):
    decision = interrupt({'kind': 'requirements_approval', 'analysis': state['analysis']})
    if decision not in ('approve', 'reject'):
        raise ValueError('Invalid approval decision')
    return {'decision': decision, 'status': 'approved' if decision == 'approve' else 'rejected', 'phase': 'test_design' if decision == 'approve' else 'rejected'}

@observe('design_node')
def design_node(state):
    try:
        criteria = criteria_for(state['requirement'])
        cases = design(state['requirement'], state['analysis'], state.get('decision') == 'approve', state['mode'], criteria)
        return {'criteria': criteria, 'test_cases': cases, 'phase': 'test_data'}
    except Exception as exc:
        return {'phase': 'failed', 'errors': [{'agent': 'test_design', 'kind': type(exc).__name__, 'message': 'Test Design failed validation or provider execution. No complete test package is available.'}]}

@observe('data_node')
def data_node(state):
    try:
        data = generate_data(state['requirement'], state['test_cases'], state['mode'])
        return {'test_data': data, 'phase': 'evaluate'}
    except Exception as exc:
        return {'phase': 'failed', 'errors': [{'agent': 'test_data', 'kind': type(exc).__name__, 'message': 'Test Data failed validation or provider execution. Review partial test design.'}]}

@observe('evaluate_node')
def evaluate_node(state):
    return {'metrics': evaluate_coverage(state['test_cases'], state['criteria'], state['analysis']['scenarios'], state['test_data']), 'phase': 'ready_for_review'}

builder = StateGraph(QAState)
builder.add_node('analyze', analyze_node)
builder.add_node('review', review_node)
builder.add_node('test_design', design_node)
builder.add_node('test_data', data_node)
builder.add_node('evaluate', evaluate_node)
builder.add_edge(START, 'analyze')
builder.add_conditional_edges('analyze', lambda state: END if state['phase'] == 'failed' else 'review')
builder.add_conditional_edges('review', lambda state: 'test_design' if state['decision'] == 'approve' else END)
builder.add_conditional_edges('test_design', lambda state: END if state['phase'] == 'failed' else 'test_data')
builder.add_conditional_edges('test_data', lambda state: END if state['phase'] == 'failed' else 'evaluate')
builder.add_edge('evaluate', END)
graph = DurableGraph(builder)

def config(run_id: str):
    return {'configurable': {'thread_id': run_id}}

def snapshot(run_id: str):
    snap = graph.get_state(config(run_id))
    if not snap.values:
        raise KeyError(run_id)
    return {'run_id': run_id, **snap.values}

def start(requirement: str):
    run_id = str(uuid4())
    graph.invoke({'requirement': requirement}, config(run_id))
    return snapshot(run_id)

decision_lock = RLock()

def decide(run_id: str, decision: str):
    # Serialize review transitions in this single-process local server.
    with decision_lock:
        return _decide(run_id, decision)

def _decide(run_id: str, decision: str):
    if decision not in ('approve', 'reject'):
        raise ValueError('Decision must be approve or reject')
    current = graph.get_state(config(run_id))
    if not current.values:
        raise KeyError(run_id)
    if not current.next or current.values.get('status') != 'awaiting_approval':
        raise RuntimeError('Run is not awaiting approval')
    graph.invoke(Command(resume=decision), config(run_id))
    return snapshot(run_id)


def edit_case(run_id, case_id, edit):
    with decision_lock:
        current = snapshot(run_id)
        if current.get('phase') != 'ready_for_review':
            raise RuntimeError('Test package is not ready for review')
        cases = [dict(case) for case in current['test_cases']]
        selected = next((case for case in cases if case['id'] == case_id), None)
        if selected is None:
            raise KeyError(case_id)
        selected.update(edit.model_dump())
        if selected['review_status'] == 'reviewed' and selected['expected_result']['needs_review']:
            raise ValueError('Confirm the expected result before marking the case reviewed')
        # Edited expected results invalidate linked fixture review.
        data = [dict(item) for item in current['test_data']]
        for item in data:
            if item['test_case_id'] == case_id:
                item['expected_behavior'] = selected['expected_result']['description']
                item['needs_review'] = True
        metrics = evaluate_coverage(cases, current['criteria'], current['analysis']['scenarios'], data)
        graph.update_state(config(run_id), {'test_cases': cases, 'test_data': data, 'metrics': metrics})
        return snapshot(run_id)


def edit_data(run_id, data_id, edit):
    from .models.test_data import TestData
    with decision_lock:
        current = snapshot(run_id)
        if current.get('phase') != 'ready_for_review':
            raise RuntimeError('Test package is not ready for review')
        data = [dict(item) for item in current['test_data']]
        selected = next((item for item in data if item['id'] == data_id), None)
        if selected is None:
            raise KeyError(data_id)
        candidate = TestData.model_validate(selected | edit.model_dump())
        case = next(case for case in current['test_cases'] if case['id'] == candidate.test_case_id)
        if not candidate.needs_review and (case['expected_result']['needs_review'] or case['review_status'] != 'reviewed'):
            raise ValueError('Review the linked test case before confirming its fixture')
        selected.update(candidate.model_dump())
        graph.update_state(config(run_id), {'test_data': data})
        return snapshot(run_id)
