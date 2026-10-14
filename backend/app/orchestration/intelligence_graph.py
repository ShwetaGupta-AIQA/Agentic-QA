from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from ..rag.retriever import search
from ..services.regression_impact import analyze as impact
from ..agents.defect_analysis import analyze as defect

class State(TypedDict,total=False):
 task:str
 request:object
 result:dict

def route(state):return state['task']
builder=StateGraph(State)
for name,fn in [('search',search),('impact',impact),('defect',defect)]:
 def node(state,fn=fn):return {'result':fn(state['request'])}
 builder.add_node(name,node);builder.add_edge(name,END)
builder.add_conditional_edges(START,route,{'search':'search','impact':'impact','defect':'defect'})
graph=builder.compile()

def run(task,request):
 if task not in ['search','impact','defect']:raise ValueError('Unknown intelligence task')
 return graph.invoke({'task':task,'request':request})['result']
