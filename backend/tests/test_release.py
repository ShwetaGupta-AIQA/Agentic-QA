import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.models.release import ReleaseEvidence,ReleaseRequest,ReleaseDecision,Explanation
from app.services import quality_gates as gates,release_auth as auth,release_service as service,evidence_aggregator as aggregate,execution_service as executions
from app.agents import release_readiness as agent
from app.services.suite_registry import REGISTRY

POLICY=json.loads(aggregate.POLICY_FILE.read_text())
def evidence(**changes):
 now=datetime.now(timezone.utc).isoformat()
 values=dict(release_id='commerce-test',tests_total=100,tests_passed=100,tests_failed=0,tests_errors=0,tests_skipped=0,tests_blocked=0,requirement_coverage=100.0,critical_defects_open=0,high_defects_open=0,risk_level='low',unresolved_regression_risks=0,oldest_execution_at=now,review_at=now,execution_approved=True,contract_matches=True,execution_complete=True,source_ids=['execution:test','review:test'])
 values.update(changes);return ReleaseEvidence(**values)
@pytest.mark.parametrize('changes,expected',[
 ({},'GO'),({'high_defects_open':1},'CONDITIONAL_GO'),({'risk_level':'medium'},'CONDITIONAL_GO'),
 ({'critical_defects_open':1},'NO_GO'),({'high_defects_open':6},'NO_GO'),({'requirement_coverage':89.0},'NO_GO'),
 ({'tests_passed':94,'tests_failed':6},'NO_GO'),({'tests_passed':95,'tests_failed':5},'GO'),
 ({'tests_passed':97,'tests_skipped':3},'NO_GO'),({'tests_passed':99,'tests_blocked':1},'NO_GO'),
 ({'execution_complete':False},'NO_GO'),({'execution_approved':False},'NO_GO'),({'contract_matches':False},'NO_GO'),
 ({'critical_defects_open':None},'NO_GO'),({'risk_level':None},'NO_GO'),({'oldest_execution_at':None},'NO_GO'),
 ({'review_at':(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()},'NO_GO'),
 ({'oldest_execution_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()},'NO_GO'),
 ({'tests_total':500,'tests_passed':460,'tests_failed':40,'requirement_coverage':87.0,'critical_defects_open':2},'NO_GO'),
 ({'tests_total':100000,'tests_passed':94999,'tests_failed':5001},'NO_GO'),
])
def test_gate_cases(changes,expected):
 result=gates.evaluate(evidence(**changes),POLICY)
 assert result['recommendation']==expected
 assert all(item['source_ids'] for item in result['gates'])
def test_missing_and_zero():
 assert gates.evaluate(ReleaseEvidence(release_id='empty'),POLICY)['recommendation']=='NO_GO'
 assert gates.evaluate(evidence(tests_total=0,tests_passed=0),POLICY)['recommendation']=='NO_GO'
def test_invalid_counts_and_nonfinite():
 with pytest.raises(ValidationError):evidence(tests_passed=101)
 with pytest.raises(ValidationError):evidence(requirement_coverage=float('nan'))
@pytest.mark.parametrize('header,name',[('','Reviewer'),('Bearer wrong','Reviewer'),('Bearer '+ 'x'*40,'Other')])
def test_auth_denied(monkeypatch,header,name):
 monkeypatch.setenv('QA_RELEASE_REVIEW_TOKEN','x'*40);monkeypatch.setenv('QA_RELEASE_REVIEWER','Reviewer')
 with pytest.raises(PermissionError):auth.authorize(header,name)
def test_auth_configuration(monkeypatch):
 monkeypatch.delenv('QA_RELEASE_REVIEW_TOKEN',raising=False)
 with pytest.raises(PermissionError):auth.authorize('Bearer secret','local-reviewer')
 monkeypatch.setenv('QA_RELEASE_REVIEW_TOKEN','x'*40);monkeypatch.setenv('QA_RELEASE_REVIEWER','Reviewer')
 auth.authorize('Bearer '+'x'*40,'Reviewer')
@pytest.fixture
def snapshot(tmp_path,monkeypatch):
 for module in [aggregate,service]:monkeypatch.setattr(module,'ROOT',tmp_path)
 for name in ['POLICY_FILE','MANIFEST_FILE']:
  old=getattr(aggregate,name);target=tmp_path/old.name;target.write_bytes(old.read_bytes());monkeypatch.setattr(aggregate,name,target)
 reviews=tmp_path/'reviews';reviews.mkdir()
 monkeypatch.setattr(aggregate,'REVIEWS',reviews);monkeypatch.setattr(service,'REVIEWS',reviews)
 monkeypatch.setattr(service,'REPORTS',tmp_path/'assessments');monkeypatch.setattr(executions,'REPORT_ROOT',tmp_path/'executions')
 monkeypatch.setattr(aggregate,'context_fingerprint',lambda:'fixture');monkeypatch.setattr(service,'context_fingerprint',lambda:'fixture')
 key=str(uuid4());now=datetime.now(timezone.utc).isoformat();rows=[]
 for suite,entry in REGISTRY.items():
  for node in entry['nodes']:rows.append(dict(test_id=suite,name=node.split('::')[1],type='UI' if '/ui/' in node else 'API',status='passed'))
 record=dict(execution_id=key,environment='local',test_ids=list(REGISTRY),status='passed',results=rows,passed=len(rows),failed=0,errors=0,skipped=0,approved=True,contract_version='commerce-v1',source_fingerprint='fixture',completed_at=now)
 executions.save(executions.directory(key),record)
 review=str(uuid4());reviewpath=reviews/(review+'.json');reviewpath.write_text(json.dumps(dict(review_id=review,release_id='commerce-test',reviewed_at=now,defects=[],risk_level='low',unresolved_regression_risks=0)))
 return ReleaseRequest(release_id='commerce-test',execution_ids=[key],review_id=review)
def decision(record,**changes):
 data=dict(decision='GO',reviewer='Reviewer',assessment_hash=record['assessment_hash'],reason='Reviewed all test evidence');data.update(changes);return ReleaseDecision(**data)
def test_aggregate_dedup_and_missing_review(snapshot):
 result=aggregate.gather(snapshot);assert result['evidence']['tests_total']==15;assert result['evidence']['requirement_coverage']==100
 other=str(uuid4());record=executions.get(snapshot.execution_ids[0]);record['execution_id']=other;executions.save(executions.directory(other),record)
 snapshot.execution_ids.append(other);assert aggregate.gather(snapshot)['evidence']['tests_total']==15
 snapshot.review_id=None;assert aggregate.gather(snapshot)['evidence']['critical_defects_open'] is None
def test_legacy_provenance(snapshot):
 record=executions.get(snapshot.execution_ids[0]);record.pop('completed_at');record.pop('source_fingerprint');executions.save(executions.directory(record['execution_id']),record)
 result=service.assess(snapshot);assert result['evaluation']['recommendation']=='NO_GO'
def test_authorization_and_replay(snapshot):
 record=service.assess(snapshot);assert record['evaluation']['recommendation']=='GO';assert agent.available(record['assessment_id'])
 result=service.decide(record['assessment_id'],decision(record));assert result['status']=='authorized';assert not agent.available(record['assessment_id'])
 with pytest.raises(RuntimeError):service.decide(record['assessment_id'],decision(record))
@pytest.mark.parametrize('mutation',['source','policy','fingerprint','hash','checkpoint','expiry'])
def test_changed_assessment_rejected(snapshot,monkeypatch,mutation):
 record=service.assess(snapshot)
 if mutation=='source':executions.directory(snapshot.execution_ids[0]).joinpath('record.json').write_text('{}')
 if mutation=='policy':aggregate.POLICY_FILE.write_text('{}')
 if mutation=='fingerprint':monkeypatch.setattr(service,'context_fingerprint',lambda:'changed')
 if mutation=='hash':record['assessment_hash']='changed'
 if mutation=='checkpoint':monkeypatch.setattr(agent,'available',lambda key:False)
 if mutation=='expiry':monkeypatch.setattr(service,'evaluate',lambda e,p:gates.evaluate(e,p,datetime.now(timezone.utc)+timedelta(days=2)))
 with pytest.raises(RuntimeError):service.decide(record['assessment_id'],decision(record))
def test_conditional_and_no_override(snapshot):
 reviewpath=aggregate.REVIEWS/(snapshot.review_id+'.json');review=json.loads(reviewpath.read_text());review['defects']=[dict(id='D1',severity='high',status='open')];reviewpath.write_text(json.dumps(review))
 record=service.assess(snapshot);assert record['evaluation']['recommendation']=='CONDITIONAL_GO'
 with pytest.raises(RuntimeError):service.decide(record['assessment_id'],decision(record))
 with pytest.raises(ValueError):service.decide(record['assessment_id'],decision(record,decision='CONDITIONAL_GO'))
 assert service.decide(record['assessment_id'],decision(record,decision='CONDITIONAL_GO',conditions_acknowledged=True))['status']=='authorized'
 review['defects'][0]['severity']='critical';reviewpath.write_text(json.dumps(review));record=service.assess(snapshot)
 with pytest.raises(RuntimeError):service.decide(record['assessment_id'],decision(record))
 assert service.decide(record['assessment_id'],decision(record,decision='NO_GO'))['status']=='rejected'
def test_llm_cannot_change_gates(monkeypatch):
 result=gates.evaluate(evidence(critical_defects_open=1),POLICY)
 def malicious(*args):return Explanation.model_validate(dict(summary='GO',recommendation='GO'))
 monkeypatch.setattr(agent,'structured_call',malicious)
 state=dict(evaluation=result,request=dict(explanation_mode='llm'),aggregate=dict(evidence={}))
 output=agent.explanation_node(state);assert output['explanation']['mode']=='llm_failed';assert result['recommendation']=='NO_GO'

def test_browser_reviewer_preflight():
 from fastapi.testclient import TestClient
 from app.main import app
 response=TestClient(app).options('/releases/evidence-review',headers={'Origin':'http://127.0.0.1:5174','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
 assert response.status_code==200
 assert 'authorization' in response.headers['access-control-allow-headers'].lower()
