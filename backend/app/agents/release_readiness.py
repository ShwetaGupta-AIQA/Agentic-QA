from ..telemetry import observe
import hashlib,json
from typing import TypedDict
from uuid import uuid4
from datetime import datetime,timezone
from langgraph.graph import StateGraph,START,END
from ..persistence import DurableGraph
from langgraph.types import interrupt,Command
from ..models.release import ReleaseEvidence,Explanation
from ..services.evidence_aggregator import gather
from ..services.quality_gates import evaluate
from ..services.model_adapter import structured_call

class State(TypedDict,total=False):
 request:dict
 aggregate:dict
 evaluation:dict
 explanation:dict
 decision:dict
 status:str

@observe('evidence_node')
def evidence_node(state):
 from ..models.release import ReleaseRequest
 return {'aggregate':gather(ReleaseRequest.model_validate(state['request']))}
@observe('gates_node')
def gates_node(state):
 result=evaluate(ReleaseEvidence.model_validate(state['aggregate']['evidence']),state['aggregate']['policy'])
 from ..telemetry import emit
 emit('release_gates',operation='quality_gates',evidence_count=len(state['aggregate']['sources']),status=result['recommendation'])
 return {'evaluation':result}
@observe('explanation_node')
def explanation_node(state):
 decision=state['evaluation'];mode=state['request']['explanation_mode']
 failures=[gate for gate in decision['gates'] if gate['status']!='PASS']
 explanation={'summary':decision['recommendation']+' from deterministic gates. '+('Review all failed or unknown gates.' if failures else 'Required gates passed; final human authorization remains separate.'),
  'remediations':[{'gate_id':gate['id'],'action':gate['remediation']} for gate in failures],'mode':'demo'}
 if mode=='llm':
  try:
   result=structured_call('Explain these deterministic gate results. Do not decide, authorize, override gates or claim missing evidence passed. Use supplied gate IDs only.',
      {'evaluation':decision,'evidence':state['aggregate']['evidence']},Explanation)
   if any(set(item)!= {'gate_id','action'} or item['gate_id'] not in {gate['id'] for gate in decision['gates']} for item in result.remediations):
    raise ValueError('Invalid explanation references')
   explanation={**result.model_dump(),'mode':'llm','note':'AI explanation; the deterministic recommendation above is authoritative'}
  except Exception as exc:explanation.update(mode='llm_failed',error_kind=type(exc).__name__,note='Model explanation failed; deterministic gate results remain authoritative')
 return {'explanation':explanation,'status':'awaiting_review'}
def reviewer_node(state):
 decision=interrupt({'kind':'release_authorization','recommendation':state['evaluation']['recommendation']})
 return {'decision':decision,'status':'authorized' if decision['decision']!='NO_GO' else 'rejected'}
builder=StateGraph(State)
for key,fn in [('evidence',evidence_node),('gates',gates_node),('explain',explanation_node),('human_review',reviewer_node)]:builder.add_node(key,fn)
builder.add_edge(START,'evidence');builder.add_edge('evidence','gates');builder.add_edge('gates','explain');builder.add_edge('explain','human_review');builder.add_edge('human_review',END)
graph=DurableGraph(builder)
def config(key):return {'configurable':{'thread_id':key}}
def start(request,key):
 graph.invoke({'request':request.model_dump()},config(key))
 return graph.get_state(config(key)).values
def resume(key,decision):return graph.invoke(Command(resume=decision),config(key))
def available(key):return bool(graph.get_state(config(key)).next)
