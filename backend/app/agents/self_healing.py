import json,difflib,asyncio
from typing import TypedDict
from uuid import uuid4
from langgraph.graph import StateGraph,START,END
from ..services.repair_validator import validate,VALIDATION_ROOT
from ..services.locator_analyzer import propose
from ..services import patch_service as patches
from ..mcp.client import request as mcp_request

class State(TypedDict,total=False):
 baseline:dict
 proposal:dict
 dom:dict
 proposal_id:str
def inspect(state):
 baseline=state['baseline'];key=baseline['validation_id']
 dom_file=VALIDATION_ROOT/key/'evidence/test_coupon_locator/dom.json'
 dom=state['dom'] if 'dom' in state else json.loads(dom_file.read_text(encoding='utf-8')) if dom_file.is_file() else {}
 candidates=propose({'category':baseline['category'],'intent':'apply_coupon'},dom)
 original=json.loads(patches.LOCATORS.read_text(encoding='utf-8'))['coupon']
 return {'proposal':{'proposal_id':state.get('proposal_id',str(uuid4())),'target':'coupon','status':'proposed' if candidates else 'ineligible',
    'baseline':baseline,'original_locator':original,'original_hash':patches.digest(patches.LOCATORS),'context_hash':patches.context_hash(),'candidates':candidates,
    'note':'DOM candidates are suggestions. Full coupon test must pass before human approval. Assertion, ambiguous locator and infrastructure failures are ineligible.'}}
builder=StateGraph(State);builder.add_node('inspect_dom',inspect);builder.add_edge(START,'inspect_dom');builder.add_edge('inspect_dom',END);graph=builder.compile()
def demonstrate():
 with patches.LOCK:
  before=patches.context_hash();source=patches.digest(patches.LOCATORS)
  baseline=validate('baseline')
  if before!=patches.context_hash() or source!=patches.digest(patches.LOCATORS):raise RuntimeError('Source changed during baseline reproduction')
  key=str(uuid4())
  pending={'proposal_id':key,'target':'coupon','status':'inspecting','baseline':baseline,'original_hash':source,'context_hash':before,'original_locator':json.loads(patches.LOCATORS.read_text(encoding='utf-8'))['coupon'],'candidates':[],'note':'MCP evidence inspection is pending'}
  patches.save(pending)
  dom_file=VALIDATION_ROOT/baseline['validation_id']/'evidence/test_coupon_locator/dom.json'
  if dom_file.is_file():
   try:evidence=asyncio.run(mcp_request('inspect_approved_dom',{'proposal_id':key}));dom=evidence['dom']
   except Exception:
    pending.update(status='mcp_failed',note='MCP evidence inspection failed; no repair may be applied');patches.save(pending);raise RuntimeError('MCP evidence inspection failed')
  else:dom={}
  record=graph.invoke({'baseline':baseline,'dom':dom,'proposal_id':key})['proposal']
  record['mcp_evidence']={'tool':'inspect_approved_dom' if dom_file.is_file() else None,'transport':'private stdio' if dom_file.is_file() else None}
  patches.save(record);return record
def validate_proposal(key,candidate):
 with patches.LOCK:
  record=patches.load(key)
  if record['status'] not in ['proposed','validated']:raise RuntimeError('Proposal is not available for validation')
  if candidate not in {item['id'] for item in record['candidates']}:raise ValueError('Candidate was not proposed from the evidence')
  if patches.digest(patches.LOCATORS)!=record['original_hash']:raise RuntimeError('Locator file changed; create a new proposal')
  if record.get('context_hash')!=patches.context_hash():raise RuntimeError('Test or SUT context changed; recreate proposal')
  validation=validate(candidate)
  if record['context_hash']!=patches.context_hash():raise RuntimeError('Test or SUT context changed during validation')
  record.update(selected_candidate=candidate,validation=validation,status='validated' if validation['passed'] else 'proposed')
  before=patches.LOCATORS.read_text(encoding='utf-8');after_data=json.loads(before)
  from ..services.locator_analyzer import CANDIDATES
  after_data['coupon']=CANDIDATES[candidate];after=json.dumps(after_data,indent=2)+'\n'
  record['patch_preview']='\n'.join(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile='locators.json',tofile='locators.json',lineterm=''))
  result_file=VALIDATION_ROOT/validation['validation_id']/'result.json'
  if validation['passed']:record['validation_hash']=patches.digest(result_file)
  patches.save(record);return record
def apply_and_regress(key,decision):
 record=patches.apply(key,decision)
 if record['status']=='applied':
  regression=validate('baseline');record['regression']=regression;record['status']='applied' if regression['passed'] else 'applied_regression_failed';patches.save(record)
 return record
