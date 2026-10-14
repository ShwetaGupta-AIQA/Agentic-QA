from pathlib import Path
from uuid import uuid4
from unittest.mock import patch,MagicMock
import json
import subprocess
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.execution import AutomationRequest
from app.agents.automation_agent import plan
from app.services.suite_registry import REGISTRY,resolve
from app.services import execution_service as service
from automation.worker import classify,parse_junit
from sut.ecommerce.app import app as commerce,reset

client=TestClient(app)

@pytest.mark.parametrize('payload',[
 {'test_ids':['ECOM-001'],'approved':False},
 {'test_ids':['ECOM-001'],'approved':True,'environment':'staging'},
 {'test_ids':['ECOM-001'],'approved':True,'command':'anything'},
 {'test_ids':[],'approved':True},
])
def test_invalid_execution_requests_blocked(payload):
 assert client.post('/executions',json=payload).status_code==422

@pytest.mark.parametrize('ids', [['unknown'],['../anything'],['-k'],['ECOM-001','ECOM-001'],['TC-001']])
def test_registry_rejects_unknown_duplicate_or_generated_ids(ids):
 with pytest.raises(ValueError):resolve(ids)

def test_catalog_and_graph_plan():
 assert len(client.get('/automation/suites').json())==10
 request=AutomationRequest(test_ids=list(REGISTRY),approved=True)
 result=plan(request)
 assert result['status']=='planned' and len(result['nodes'])==15
 assert all(node.startswith('automation/') for node in result['nodes'])

def test_api_queues_only_fixed_ids():
 with patch('app.services.execution_service.submit',return_value={'execution_id':str(uuid4()),'status':'queued','test_ids':['ECOM-001']}) as submit:
  assert client.post('/executions',json={'test_ids':['ECOM-001'],'approved':True}).status_code==202
  assert submit.call_args.args[0].test_ids==['ECOM-001']

def test_artifact_traversal_blocked(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'REPORT_ROOT',tmp_path)
 key=str(uuid4());path=tmp_path/key
 service.save(path,{'execution_id':key,'status':'passed','artifacts':['pytest.log']})
 (path/'pytest.log').write_text('evidence')
 assert service.artifact(key,'pytest.log').is_file()
 with pytest.raises(KeyError):service.artifact(key,'../outside')
 assert client.get(f'/executions/{key}/artifacts/missing').status_code==404

def test_interrupted_record_is_not_retried(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'REPORT_ROOT',tmp_path)
 key=str(uuid4());service.save(tmp_path/key,{'execution_id':key,'status':'running','artifacts':[]})
 assert service.get(key)['status']=='error'

def test_environment_excludes_provider_secrets(monkeypatch):
 monkeypatch.setenv('QA_LLM_API_KEY','private');monkeypatch.setenv('OPENROUTER_API_KEY','private')
 assert 'QA_LLM_API_KEY' not in service.clean_environment()
 assert 'OPENROUTER_API_KEY' not in service.clean_environment()

def test_failure_classification():
 failure=ET.fromstring('<failure message="AssertionError: expected rejection"/>')
 assert classify(failure)=='product_assertion'
 assert classify(ET.fromstring('<failure message="NameError: unknown fixture"/>'))=='test_script_error'
 assert classify(ET.fromstring('<error message="Browser unavailable"/>'))=='infrastructure_error'

def test_junit_parser_preserves_ui_api_identity(tmp_path):
 xml=tmp_path/'junit.xml';xml.write_text('<testsuites><testsuite><testcase classname="automation.api.test_ecommerce" name="test_valid_coupon" time="0.2"/><testcase classname="automation.ui.test_ecommerce" name="test_valid_coupon" time="0.4"><failure message="AssertionError: mismatch"/></testcase></testsuite></testsuites>')
 rows=parse_junit(xml,['ECOM-003'])
 assert [row['type'] for row in rows]==['API','UI']
 assert rows[1]['classification']=='product_assertion'

def test_worker_timeout_stops_owned_process_and_records_timeout(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'REPORT_ROOT',tmp_path)
 key=str(uuid4());service.save(tmp_path/key,{'execution_id':key,'status':'queued','test_ids':['ECOM-001'],'artifacts':[]})
 process=MagicMock();process.wait.side_effect=subprocess.TimeoutExpired('owned worker',1)
 service.slots.acquire()
 with patch('app.services.execution_service.subprocess.Popen',return_value=process),patch('app.services.execution_service.stop_tree') as stop:
  service.execute(key,['ECOM-001'])
 stop.assert_called_once_with(process)
 assert service.get(key)['status']=='timeout'

def test_sut_stock_coupon_checkout_and_reuse():
 reset();sut=TestClient(commerce)
 assert sut.post('/cart',json={'product_id':'P1','quantity':6}).status_code==409
 assert sut.post('/cart',json={'product_id':'P1','quantity':1}).status_code==200
 assert sut.post('/coupon',json={'code':'SAVE10'}).json()['payable']=='900.00'
 assert sut.post('/checkout').json()['id']=='ORDER-001'
 sut.post('/cart',json={'product_id':'P1','quantity':1})
 assert sut.post('/coupon',json={'code':'SAVE10'}).status_code==409

def test_sut_expiry_boundary_and_reset():
 reset('2030-01-02T00:00:00Z');sut=TestClient(commerce)
 sut.post('/cart',json={'product_id':'P1','quantity':1})
 assert sut.post('/coupon',json={'code':'SAVE10'}).status_code==400
 reset('2030-01-01T23:59:59Z');sut.post('/cart',json={'product_id':'P1','quantity':1})
 assert sut.post('/coupon',json={'code':'SAVE10'}).status_code==200
 reset();assert sut.get('/cart').json()['items']==[]

def test_sut_strict_quantity_and_empty_checkout():
 reset();sut=TestClient(commerce)
 assert sut.post('/cart',json={'product_id':'P1','quantity':True}).status_code==422
 assert sut.post('/checkout').status_code==400
