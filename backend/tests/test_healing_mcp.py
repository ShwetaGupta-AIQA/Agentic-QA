import asyncio,json
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.healing import HealingDecision
from app.services.locator_analyzer import propose,CANDIDATES
from app.services import patch_service as patches
from app.mcp import tool_registry as tools
from app.mcp.client import validate_arguments

BUTTON={'tag':'BUTTON','role':'button','name':'Apply coupon','testid':'apply-coupon','visible':True,'enabled':True}

@pytest.mark.parametrize('category',['product_assertion','infrastructure_error','timeout','data_failure','test_script_error','ambiguous_locator'])
def test_non_locator_failures_ineligible(category):
 assert propose({'category':category,'intent':'apply_coupon'},{'buttons':[BUTTON]})==[]

def test_unique_semantic_locator_and_ambiguous_dom():
 assert len(propose({'category':'locator_not_found','intent':'apply_coupon'},{'buttons':[BUTTON]}))==2
 assert propose({'category':'locator_not_found','intent':'apply_coupon'},{'buttons':[BUTTON,BUTTON]})==[]
 assert propose({'category':'locator_not_found','intent':'checkout'},{'buttons':[BUTTON]})==[]
 assert propose({'category':'locator_not_found','intent':'apply_coupon'},{'buttons':[BUTTON|{'enabled':False}]})==[]

@pytest.fixture
def proposal(tmp_path,monkeypatch):
 source=tmp_path/'locators.json';source.write_text(json.dumps({'coupon':{'kind':'css','value':'#apply-coupon'}}))
 monkeypatch.setattr(patches,'LOCATORS',source);monkeypatch.setattr(patches,'REPORTS',tmp_path/'proposals');monkeypatch.setattr(patches,'VALIDATION_ROOT',tmp_path/'validation')
 key=str(uuid4());validation_id=str(uuid4());evidence=patches.VALIDATION_ROOT/validation_id/'result.json';evidence.parent.mkdir(parents=True)
 evidence.write_text(json.dumps({'passed':True,'matches':1,'full_test':'test_coupon_locator'}))
 record={'proposal_id':key,'target':'coupon','status':'validated','original_locator':{'kind':'css','value':'#apply-coupon'},'original_hash':patches.digest(source),'context_hash':patches.context_hash(),
  'candidates':[{'id':'role_coupon','locator':CANDIDATES['role_coupon']}],'selected_candidate':'role_coupon',
  'validation':{'validation_id':validation_id,'passed':True},'validation_hash':patches.digest(evidence),'baseline':{'validation_id':str(uuid4()),'category':'locator_not_found'}}
 patches.save(record);return record

def decision(record,**changes):
 return HealingDecision.model_validate({'decision':'approve','reviewer':'Test reviewer','validation_id':record['validation']['validation_id'],'approved':True}|changes)

def test_approved_locator_patch_preserves_other_fields_and_audits(proposal):
 result=patches.apply(proposal['proposal_id'],decision(proposal))
 assert json.loads(patches.LOCATORS.read_text())=={'coupon':CANDIDATES['role_coupon']}
 assert result['status']=='applied' and result['audit']['reviewer']=='Test reviewer'
 assert result['audit']['scope'].startswith('coupon locator only')

@pytest.mark.parametrize('change',[{'approved':False},{'validation_id':str(uuid4())}])
def test_missing_approval_or_stale_review_blocks_patch(proposal,change):
 before=patches.digest(patches.LOCATORS)
 with pytest.raises((RuntimeError,ValueError)):patches.apply(proposal['proposal_id'],decision(proposal,**change))
 assert patches.digest(patches.LOCATORS)==before

def test_failed_validation_blocks_patch(proposal):
 proposal['validation']['passed']=False;patches.save(proposal)
 with pytest.raises(RuntimeError):patches.apply(proposal['proposal_id'],decision(proposal))

def test_source_change_blocks_stale_patch(proposal):
 patches.LOCATORS.write_text('changed')
 with pytest.raises(RuntimeError,match='changed'):patches.apply(proposal['proposal_id'],decision(proposal))

def test_tampered_evidence_blocks_patch(proposal):
 (patches.VALIDATION_ROOT/proposal['validation']['validation_id']/'result.json').write_text('changed')
 with pytest.raises(RuntimeError,match='evidence'):patches.apply(proposal['proposal_id'],decision(proposal))

def test_rejection_does_not_modify_source(proposal):
 before=patches.digest(patches.LOCATORS)
 assert patches.apply(proposal['proposal_id'],decision(proposal,decision='reject',approved=False))['status']=='rejected'
 assert patches.digest(patches.LOCATORS)==before

def test_repeated_decision_blocked(proposal):
 patches.apply(proposal['proposal_id'],decision(proposal,decision='reject',approved=False))
 with pytest.raises(RuntimeError):patches.apply(proposal['proposal_id'],decision(proposal))

def test_approval_boolean_must_be_real_boolean():
 from pydantic import ValidationError
 with pytest.raises(ValidationError):HealingDecision(decision='approve',reviewer='Reviewer',validation_id='id',approved=1)

def test_invalid_target_and_arbitrary_candidate_not_accepted():
 client=TestClient(app)
 assert client.post('/healing/not-uuid/validate',json={'candidate':'arbitrary-selector'}).status_code==422
 assert client.post('/healing/not-uuid/decision',json={'decision':'approve','reviewer':'x','validation_id':'id','approved':True,'path':'outside.py'}).status_code==422

def test_mcp_authentication_and_scope_checks(monkeypatch):
 monkeypatch.setenv('QA_MCP_SESSION_TOKEN','x'*40);monkeypatch.setenv('QA_MCP_SCOPES','executions:read')
 tools.authorize('x'*40,'get_execution')
 with pytest.raises(PermissionError):tools.authorize('wrong','get_execution')
 with pytest.raises(PermissionError):tools.authorize('x'*40,'read_artifact')
 with pytest.raises(PermissionError):tools.authorize('x'*40,'apply_patch')

def test_mcp_client_rejects_unknown_tool_token_injection_and_url():
 for name,args in [('apply_patch',{}),('get_execution',{'execution_id':'id','token':'secret'}),('inspect_approved_dom',{'url':'https://anything'})]:
  with pytest.raises(ValueError):validate_arguments(name,args)

def test_mcp_artifact_traversal_blocked(tmp_path,monkeypatch):
 key=str(uuid4());path=tmp_path/'reports/executions'/key;path.mkdir(parents=True)
 (path/'record.json').write_text(json.dumps({'status':'passed','artifacts':['junit.xml']}));(path/'junit.xml').write_text('<testsuites/>')
 monkeypatch.setattr(tools,'ROOT',tmp_path);monkeypatch.setenv('QA_MCP_SESSION_TOKEN','x'*40);monkeypatch.setenv('QA_MCP_SCOPES','artifacts:read')
 assert tools.read_artifact('x'*40,key,'junit.xml')['text']=='<testsuites/>'
 with pytest.raises(ValueError):tools.read_artifact('x'*40,key,'../outside.txt')

def test_mcp_read_does_not_mutate_running_record(tmp_path,monkeypatch):
 key=str(uuid4());path=tmp_path/'reports/executions'/key;path.mkdir(parents=True)
 text=json.dumps({'status':'running','artifacts':[]});(path/'record.json').write_text(text)
 monkeypatch.setattr(tools,'ROOT',tmp_path);monkeypatch.setenv('QA_MCP_SESSION_TOKEN','x'*40);monkeypatch.setenv('QA_MCP_SCOPES','executions:read')
 assert tools.get_execution('x'*40,key)['status']=='running'
 assert (path/'record.json').read_text()==text

def test_labeled_healing_evaluation():
 from app.evaluate_healing import evaluate
 result=evaluate()
 assert result['samples']==11 and result['correct']==11
 assert result['ineligible_proposals']==0

def test_actual_mcp_initialization_discovers_no_mutation_tools():
 from app.mcp.client import request
 result=asyncio.run(request())
 assert len(result['tools'])==4 and result['patch_tools'] is False
 assert result['resources']==['qa://policy']
 assert all('token' not in tool['input_schema']['properties'] for tool in result['tools'])


def test_changed_test_or_sut_context_blocks_patch(proposal):
 with patch('app.services.patch_service.context_hash',return_value='changed-context'):
  with pytest.raises(RuntimeError,match='context'):patches.apply(proposal['proposal_id'],decision(proposal))
