from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from ..services.suite_registry import resolve

class AutomationState(TypedDict,total=False):
 test_ids:list[str]
 environment:str
 approved:bool
 nodes:list[str]
 status:str

def select(state):
 if state.get('approved') is not True or state.get('environment')!='local':
  raise ValueError('Human-approved local suites are required')
 return {'nodes':resolve(state['test_ids']),'status':'planned'}

builder=StateGraph(AutomationState);builder.add_node('select_approved_suite',select)
builder.add_edge(START,'select_approved_suite');builder.add_edge('select_approved_suite',END)
graph=builder.compile()

def plan(request):return graph.invoke(request.model_dump())
