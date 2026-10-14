import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import runtime,telemetry,persistence
from app.services import execution_service as executions,job_queue
from app.models.execution import AutomationRequest

def test_controlled_configuration_fails_closed(monkeypatch):
 monkeypatch.setenv('QA_DEPLOYMENT_MODE','controlled');monkeypatch.delenv('QA_API_TOKEN',raising=False)
 with pytest.raises(RuntimeError):runtime.validate()
def test_secret_files_load_without_echo(tmp_path,monkeypatch,capsys):
 file=tmp_path/'secret';file.write_text('x'*40);monkeypatch.setenv('QA_API_TOKEN_FILE',str(file));runtime.load_secrets()
 assert __import__('os').environ['QA_API_TOKEN']=='x'*40
 assert capsys.readouterr().out==''
@pytest.mark.parametrize('method,path',[('get','/releases'),('post','/executions'),('get','/workflows/example'),('get','/metrics'),('get','/docs'),('get','/ready')])
def test_demo_api_access_denied(monkeypatch,method,path):
 monkeypatch.setenv('QA_DEPLOYMENT_MODE','controlled');monkeypatch.setenv('QA_API_TOKEN','x'*40)
 response=getattr(TestClient(app),method)(path)
 assert response.status_code==401
def test_valid_gateway_token_and_liveness(monkeypatch):
 monkeypatch.setenv('QA_DEPLOYMENT_MODE','controlled');monkeypatch.setenv('QA_API_TOKEN','x'*40)
 client=TestClient(app);assert client.get('/health').status_code==200
 assert client.get('/releases/policy',headers={'X-QA-Access-Token':'x'*40}).status_code==200
 assert client.get('/metrics',headers={'X-QA-Access-Token':'wrong'}).status_code==401
def test_healing_browser_not_run_in_public_api(monkeypatch):
 monkeypatch.setenv('QA_DEPLOYMENT_MODE','controlled');monkeypatch.setenv('QA_API_TOKEN','x'*40)
 assert TestClient(app).post('/healing/demonstration',headers={'X-QA-Access-Token':'x'*40}).status_code==403
def test_raw_tracing_disallowed(monkeypatch):
 monkeypatch.setenv('QA_DEPLOYMENT_MODE','controlled');monkeypatch.setenv('QA_API_TOKEN','x'*40);monkeypatch.setenv('QA_RELEASE_REVIEW_TOKEN','y'*40)
 monkeypatch.setenv('QA_DATABASE_URL','postgresql://placeholder');monkeypatch.setenv('QA_EXECUTION_MODE','queue');monkeypatch.setenv('LANGSMITH_TRACING','true')
 with pytest.raises(RuntimeError,match='Raw'):runtime.validate()
def test_telemetry_excludes_sensitive_metadata(monkeypatch):
 rows=[];monkeypatch.setattr(telemetry.LOGGER,'info',rows.append)
 telemetry.emit('test',operation='safe',password='secret',requirement='customer-data',authorization='credential',query='private-query')
 output=json.loads(rows[0]);assert output['operation']=='safe';assert not any(value in rows[0] for value in ['secret','customer-data','credential','private-query'])
def test_span_records_failure_type_without_exception_text(monkeypatch):
 rows=[];monkeypatch.setattr(telemetry.LOGGER,'info',rows.append)
 with pytest.raises(ValueError):
  with telemetry.span('validation'):raise ValueError('private-secret')
 item=json.loads(rows[0]);assert item['error_kind']=='ValueError';assert item['status']=='error';assert 'private-secret' not in rows[0]
def test_private_queue_submission_runs_no_api_subprocess(monkeypatch,tmp_path):
 monkeypatch.setenv('QA_EXECUTION_MODE','queue');monkeypatch.setattr(executions,'REPORT_ROOT',tmp_path)
 jobs=[];monkeypatch.setattr(job_queue,'enqueue',lambda key,ids:jobs.append((key,ids)))
 monkeypatch.setattr(executions.pool,'submit',lambda *a:pytest.fail('API launched a worker'))
 record=executions.submit(AutomationRequest(test_ids=['ECOM-001'],approved=True));assert record['status']=='queued';assert jobs[0][1]==['ECOM-001'];assert record['approved']
def test_failed_enqueue_preserves_error_evidence(monkeypatch,tmp_path):
 monkeypatch.setenv('QA_EXECUTION_MODE','queue');monkeypatch.setattr(executions,'REPORT_ROOT',tmp_path)
 def fail(*args):raise RuntimeError('queue-full')
 monkeypatch.setattr(job_queue,'enqueue',fail)
 with pytest.raises(RuntimeError):executions.submit(AutomationRequest(test_ids=['ECOM-001'],approved=True))
 record=json.loads(next(tmp_path.glob('*/record.json')).read_text());assert record['status']=='error'
def test_live_queued_job_survives_api_process_restart(monkeypatch,tmp_path):
 monkeypatch.setenv('QA_EXECUTION_MODE','queue');monkeypatch.setattr(executions,'REPORT_ROOT',tmp_path);monkeypatch.setattr(job_queue,'enqueue',lambda *a:None)
 record=executions.submit(AutomationRequest(test_ids=['ECOM-001'],approved=True));monkeypatch.setattr(job_queue,'state',lambda key:'queued')
 assert executions.get(record['execution_id'])['status']=='queued'
 monkeypatch.setattr(job_queue,'state',lambda key:'error');assert executions.get(record['execution_id'])['status']=='error'
def test_memory_is_explicit_local_default(monkeypatch):
 monkeypatch.delenv('QA_DATABASE_URL',raising=False);assert persistence.saver().__class__.__name__=='InMemorySaver'

def test_optional_langsmith_exports_only_sanitized_metadata(monkeypatch):
 from unittest.mock import MagicMock
 import langsmith
 client=MagicMock();factory=MagicMock(return_value=client);monkeypatch.setattr(langsmith,'Client',factory);monkeypatch.setenv('QA_LANGSMITH_ENABLED','true')
 telemetry.emit('test-export',operation='safe',requirement='private-requirement',password='private-password')
 payload=client.create_run.call_args.kwargs
 assert payload['inputs']=={} and payload['outputs']=={}
 assert 'private-requirement' not in str(payload) and 'private-password' not in str(payload)
 assert factory.call_args.kwargs=={'hide_inputs':True,'hide_outputs':True}
