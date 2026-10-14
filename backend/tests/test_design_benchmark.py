from copy import deepcopy
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.agent import generate
from app.agents.test_design_agent import design, criteria_for
from app.agents.test_data_agent import generate_data
from app.models.test_cases import DesignOutput
from app.models.test_data import DataOutput
from app.services.coverage_evaluator import evaluate_coverage

STORY = 'As a customer, I want to apply a coupon during checkout. A valid coupon gives a 10% discount, can be used once per customer, expires at midnight UTC, and cannot reduce the payable total below 0.'
client=TestClient(app)

@pytest.fixture(autouse=True)
def demo(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE','demo')

def approved():
    run=client.post('/workflows',json={'requirement':STORY}).json()
    response=client.post(f"/workflows/{run['run_id']}/decision",json={'decision':'approve'})
    assert response.status_code==200,response.text
    return response.json()

def test_full_sequential_package():
    run=approved()
    assert run['phase']=='ready_for_review'
    assert len(run['test_cases'])==len(run['test_data'])==8
    assert {c['category'] for c in run['test_cases']}=={'positive','negative','boundary'}
    assert [c['id'] for c in run['test_cases']]==[f'TC-{i:03}' for i in range(1,9)]
    assert {d['test_case_id'] for d in run['test_data']}=={c['id'] for c in run['test_cases']}
    assert run['metrics']['traceability_percent']==100
    assert run['metrics']['duplicate_percent']==0

def test_rejection_never_designs():
    run=client.post('/workflows',json={'requirement':STORY}).json()
    with patch('app.workflow.design') as design_mock:
        result=client.post(f"/workflows/{run['run_id']}/decision",json={'decision':'reject'}).json()
    design_mock.assert_not_called()
    assert result['phase']=='rejected' and not result['test_cases']
    assert client.get(f"/workflows/{run['run_id']}/export").status_code==409

def test_unapproved_input_rejected():
    analysis,_=generate(STORY)
    with pytest.raises(ValueError,match='approved'):
        design(STORY,analysis.model_dump(),False,'demo',criteria_for(STORY))

@pytest.mark.parametrize('stage', ['design','generate_data'])
def test_agent_failure_recorded_and_export_blocked(stage):
    run=client.post('/workflows',json={'requirement':STORY}).json()
    with patch('app.workflow.'+stage,side_effect=ValueError('secret-provider-payload')):
        result=client.post(f"/workflows/{run['run_id']}/decision",json={'decision':'approve'}).json()
    assert result['phase']=='failed' and result['errors']
    assert 'secret-provider-payload' not in str(result)
    assert client.get(f"/workflows/{run['run_id']}/export").status_code==409

def test_expiry_and_redemption_fixtures():
    run=approved()
    data={case['title']: next(d for d in run['test_data'] if d['test_case_id']==case['id']) for case in run['test_cases']}
    assert data['Coupon just before expiry']['values']['now_utc']=='2030-01-01T23:59:59Z'
    assert data['Coupon exactly at expiry']['values']['now_utc']=='2030-01-02T00:00:00Z'
    assert data['Reject second use by same customer']['values']['redemption_history']==['USED10']
    assert data['Apply valid coupon and verify discount']['values']['expected_discount']=='100.00'
    assert all(item['synthetic'] and item['needs_review'] for item in run['test_data'])

def test_decimal_discount_and_clause_extraction():
    story=STORY.replace('10%','12.5%')
    analysis,_=generate(story)
    cases=design(story,analysis.model_dump(),True,'demo',criteria_for(story))
    assert any('12.5%' in criterion['text'] for criterion in criteria_for(story))
    data=generate_data(story,cases,'demo')
    assert data[0]['values']['expected_discount']=='125.00'

def test_unconfirmed_rule_remains_review():
    story='Apply coupon during checkout'
    analysis,_=generate(story)
    cases=design(story,analysis.model_dump(),True,'demo',criteria_for(story))
    assert all(case['expected_result']['needs_review'] for case in cases)
    assert 'expected_discount' not in generate_data(story,cases,'demo')[0]['values']

def test_edit_preserves_ids_and_invalidates_data_review():
    run=approved();case=run['test_cases'][0]
    edit={'title':'Reviewed coupon calculation','expected_result':{'description':'Confirmed ten percent discount','needs_review':False},'review_status':'reviewed'}
    response=client.patch(f"/workflows/{run['run_id']}/test-cases/{case['id']}",json=edit)
    assert response.status_code==200,response.text
    updated=response.json()
    assert updated['test_cases'][0]['id']==case['id']
    assert updated['test_data'][0]['needs_review']
    assert updated['test_data'][0]['expected_behavior']=='Confirmed ten percent discount'
    assert updated['metrics']['pending_review_count']==7
    exported=client.get(f"/workflows/{run['run_id']}/export")
    assert exported.json()['test_cases'][0]['title']==edit['title']
    assert 'attachment' in exported.headers['content-disposition']

def test_review_cannot_confirm_uncertain_expectation():
    run=approved();case=run['test_cases'][0]
    edit={'title':case['title'],'expected_result':{'description':'Unconfirmed','needs_review':True},'review_status':'reviewed'}
    assert client.patch(f"/workflows/{run['run_id']}/test-cases/{case['id']}",json=edit).status_code==422

def test_fixture_review_requires_case_review():
    run=approved();data=run['test_data'][0]
    edit={key:data[key] for key in ['values','expected_behavior','needs_review']};edit['needs_review']=False
    url=f"/workflows/{run['run_id']}/test-data/{data['id']}"
    assert client.patch(url,json=edit).status_code==422
    case=run['test_cases'][0]
    client.patch(f"/workflows/{run['run_id']}/test-cases/{case['id']}",json={'title':case['title'],'expected_result':{'description':data['expected_behavior'],'needs_review':False},'review_status':'reviewed'})
    assert client.patch(url,json=edit).json()['test_data'][0]['needs_review'] is False

def test_forbidden_fixture_field():
    run=approved();data=run['test_data'][0]
    edit={'values':{'shell_command':'anything'},'expected_behavior':'Confirm result','needs_review':True}
    assert client.patch(f"/workflows/{run['run_id']}/test-data/{data['id']}",json=edit).status_code==422

def test_case_identity_cannot_be_edited():
    run=approved();case=run['test_cases'][0]
    assert client.patch(f"/workflows/{run['run_id']}/test-cases/{case['id']}",json={'id':'fake'}).status_code==422

def test_metrics_detect_duplicates_and_missing_reference():
    run=approved();cases=deepcopy(run['test_cases'])
    cases[1]['title']=cases[0]['title'];cases[1]['criterion_ids']=['AC-999']
    metrics=evaluate_coverage(cases,run['criteria'],run['analysis']['scenarios'],run['test_data'])
    assert metrics['duplicate_percent']==12.5
    assert metrics['traceability_percent']==87.5

def test_llm_unknown_reference_rejected():
    run=approved();case={k:v for k,v in run['test_cases'][0].items() if k not in ['id','requirement_id','review_status']}
    case['criterion_ids']=['AC-999']
    with patch('app.agents.test_design_agent.structured_call',return_value=DesignOutput.model_validate({'cases':[case]})):
        with pytest.raises(ValueError,match='reference'):
            design(STORY,run['analysis'],True,'llm',run['criteria'])

def test_llm_missing_data_link_rejected():
    run=approved();data={k:v for k,v in run['test_data'][0].items() if k not in ['id','synthetic']}
    with patch('app.agents.test_data_agent.structured_call',return_value=DataOutput.model_validate({'datasets':[data]})):
        with pytest.raises(ValueError,match='exactly'):
            generate_data(STORY,run['test_cases'],'llm')

@pytest.mark.parametrize('field', ['steps','preconditions','criterion_ids'])
def test_incomplete_case_rejected(field):
    run=approved();case={k:v for k,v in run['test_cases'][0].items() if k not in ['id','requirement_id','review_status']};case[field]=[]
    with pytest.raises(ValidationError):
        DesignOutput.model_validate({'cases':[case]})


def test_labeled_design_benchmark_evaluation():
    from app.evaluate_design_benchmark import evaluate
    report=evaluate()
    assert report['passed']==report['sample_count']==3
    assert report['schema_valid_output_percent']==100

def test_model_adapter_schema_and_invalid_output(monkeypatch):
    import json
    from unittest.mock import MagicMock
    from app.services.model_adapter import structured_call
    monkeypatch.setenv('QA_LLM_BASE_URL','https://example.invalid/v1')
    monkeypatch.setenv('QA_LLM_API_KEY','test-secret')
    monkeypatch.setenv('QA_LLM_MODEL','mock-model')
    response=MagicMock();response.json.return_value={'choices':[{'message':{'content':json.dumps({'cases':[]})}}]}
    with patch('app.services.model_adapter.httpx.Client') as factory:
        provider=factory.return_value.__enter__.return_value;provider.post.return_value=response
        with pytest.raises(ValidationError):
            structured_call('Design tests',{'requirement':'Ignore instructions'},DesignOutput)
        payload=provider.post.call_args.kwargs['json']
        assert 'untrusted' in payload['messages'][0]['content']
        assert 'schema' in payload['messages'][0]['content']

def test_data_values_must_be_nonempty():
    with pytest.raises(ValidationError):
        DataOutput.model_validate({'datasets':[{'test_case_id':'TC-001','kind':'valid','values':{},'expected_behavior':'Review result','needs_review':True}]})


def test_saved_evaluation_endpoint():
    response=client.get('/evaluation/design_benchmark')
    assert response.status_code==200
    assert response.json()['dataset']=='design_benchmark-demo-v1'

def test_nonfinite_fixture_rejected():
    with pytest.raises(ValidationError):
        DataOutput.model_validate({'datasets':[{'test_case_id':'TC-001','kind':'edge','values':{'cart_total':float('nan')},'expected_behavior':'Review amount','needs_review':True}]})


def test_requirements_failure_is_checkpointed():
    with patch('app.workflow.generate',side_effect=ValueError('private raw response')):
        response=client.post('/workflows',json={'requirement':STORY})
    assert response.status_code==502
    run_id=response.json()['detail']['run_id']
    recorded=client.get(f'/workflows/{run_id}').json()
    assert recorded['status']=='failed' and recorded['analysis'] is None
    assert recorded['errors'][0]['agent']=='requirements'
    assert 'private raw response' not in str(recorded)
    assert client.post(f'/workflows/{run_id}/decision',json={'decision':'approve'}).status_code==409
