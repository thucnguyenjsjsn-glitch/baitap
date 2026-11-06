import pytest
from fastapi import HTTPException
from app.plan_schemas import PlanExtracted
from app.plan_service import validate_plan, order_plan
from app.plan_ai_service import DEMO_PLAN

def plan(tasks=None, deps=None):
    return PlanExtracted(tasks=tasks if tasks is not None else DEMO_PLAN['tasks'],dependencies=deps if deps is not None else DEMO_PLAN['dependencies'])

def test_example_order():
    assert order_plan(plan())['order']==['A','B','C','D']

def test_shuffled_tasks_same_order():
    assert order_plan(plan(tasks=list(reversed(DEMO_PLAN['tasks']))))['order']==['A','B','C','D']

def test_cycle():
    deps=DEMO_PLAN['dependencies']+[{'before':'D','after':'A','evidence':'D trước A'}]
    result=order_plan(plan(deps=deps))
    assert result['status']=='cycle_detected' and result['order'] is None
    assert result['cycle'][0]==result['cycle'][-1]

def test_unknown_id():
    with pytest.raises(HTTPException) as exc:
        validate_plan(plan(deps=[{'before':'X','after':'A','evidence':'X trước A'}]))
    assert exc.value.status_code==422

def test_self_dependency():
    with pytest.raises(HTTPException):
        validate_plan(plan(deps=[{'before':'A','after':'A','evidence':'A trước A'}]))

def test_duplicate_task_id():
    with pytest.raises(HTTPException):
        validate_plan(plan(tasks=DEMO_PLAN['tasks']+[DEMO_PLAN['tasks'][0]]))

def test_duplicate_edge_only_count_once():
    deps=DEMO_PLAN['dependencies']+[DEMO_PLAN['dependencies'][0]]
    result=order_plan(plan(deps=deps))
    assert result['order']==['A','B','C','D']
    assert result['validation']['duplicate_dependencies_ignored']==1

def test_no_edges():
    assert order_plan(plan(deps=[]))['order']==['A','B','C','D']

def test_empty_tasks():
    assert order_plan(plan(tasks=[],deps=[]))['order']==[]
