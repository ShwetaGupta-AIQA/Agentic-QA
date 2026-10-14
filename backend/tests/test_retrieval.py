import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch,MagicMock
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.intelligence import SearchRequest,DefectRequest,LLMFinding
from app.rag.ingestion import ingest,ingest_demo,chunks,ingest_workflow
from app.rag.retriever import search,get_source
from app.rag.vector_store import collection
from app.rag.embeddings import Embedder
from app.services.regression_impact import analyze as impact
from app.agents.defect_analysis import analyze
from app.services import execution_service as executions

@pytest.fixture(scope='module')
def knowledge_path(tmp_path_factory):
 path=tmp_path_factory.mktemp('chroma-retrieval')
 with pytest.MonkeyPatch.context() as monkey:
  monkey.setenv('QA_KNOWLEDGE_PATH',str(path));monkey.setenv('QA_EMBEDDING_MODE','demo');ingest_demo()
 return path

@pytest.fixture(autouse=True)
def config(monkeypatch,knowledge_path):
 monkeypatch.setenv('QA_KNOWLEDGE_PATH',str(knowledge_path));monkeypatch.setenv('QA_EMBEDDING_MODE','demo')
 monkeypatch.setenv('QA_MODEL_MODE','demo')

@pytest.fixture
def failed_record(tmp_path,monkeypatch):
 monkeypatch.setattr(executions,'REPORT_ROOT',tmp_path)
 key=str(uuid4())
 record={'execution_id':key,'status':'failed','test_ids':['ECOM-005'],'environment':'local','passed':0,'failed':1,'errors':0,'artifacts':['junit.xml'],
  'results':[{'test_id':'ECOM-005','name':'test_expired_coupon','type':'API','status':'failed','classification':'product_assertion','message':'Expected rejection status 400; actual status 200','duration_seconds':.1}]}
 executions.save(tmp_path/key,record)
 return record

def test_repeatable_ingestion():
 before=collection()[0].count();result=ingest_demo()
 assert result['documents']==30 and collection()[0].count()==before

def test_chunking_overlap_and_blank():
 parts=chunks('x'*1800)
 assert len(parts)==3 and parts[0][-120:]==parts[1][:120]
 with pytest.raises(ValueError):chunks('text',20,20)

def test_immutable_source_revision():
 document={'id':'REV-1','title':'Revision','text':'x'*1600,'project':'revision','kind':'requirement','source_version':'1'}
 ingest([document])
 with pytest.raises(ValueError,match='immutable'):ingest([document|{'text':'x'*800}])
 ingest([document|{'text':'changed','source_version':'2'}])

def test_duplicate_batch_identity_rejected():
 document={'id':'D','title':'Title','text':'text','kind':'defect','source_version':'1'}
 with pytest.raises(ValueError,match='Duplicate'):ingest([document,document])

def test_metadata_filtering_and_version():
 result=search(SearchRequest(query='coupon expiry midnight',kind='requirement',source_version='commerce-v1'))
 assert result['sources']
 assert all(hit['metadata']['kind']=='requirement' and hit['metadata']['source_version']=='commerce-v1' for hit in result['sources'])
 assert not search(SearchRequest(query='coupon',project='unknown'))['sources']

def test_unrelated_query_returns_no_demo_hits():
 assert not search(SearchRequest(query='astronomy nebula pulsar'))['sources']

def test_synonym_retrieval_and_citation_resolution():
 result=search(SearchRequest(query='voucher expiry boundary',kind='test'))
 assert any(hit['source_id']=='TEST-ECOM-005' for hit in result['sources'])
 for hit in result['sources']:
  assert hit['citation_id'] in {source['citation_id'] for source in get_source(hit['source_id'])}

def test_regression_impact_only_tests_and_no_execution():
 result=impact(SearchRequest(query='coupon discount increased to 15 percent'))
 assert result['impacted_tests']
 assert all(source['metadata']['kind']=='test' for source in result['sources'])
 assert any(row['test_id']=='ECOM-003' for row in result['impacted_tests'])
 assert all(row['needs_review'] for row in result['impacted_tests'])

def test_defect_observation_preserved_and_grounded(failed_record):
 report=analyze(DefectRequest(execution_id=failed_record['execution_id']))
 finding=report['findings'][0]
 assert finding['observed']==failed_record['results'][0]
 assert finding['classification']=='potential_product_defect' and finding['human_review_required']
 valid={source['citation_id'] for source in finding['sources']}
 assert set(finding['hypotheses'][0]['citation_ids'])<=valid
 assert any(source['source_id'].startswith('LOG-'+failed_record['execution_id']) for source in finding['sources'])

def test_infrastructure_is_not_product_defect(failed_record):
 row=failed_record['results'][0];row['classification']='infrastructure_error';row['status']='error';row['message']='Browser unavailable'
 executions.save(executions.directory(failed_record['execution_id']),failed_record)
 report=analyze(DefectRequest(execution_id=failed_record['execution_id']))
 assert report['findings'][0]['classification']=='execution_infrastructure_issue'

def test_timeout_has_actual_execution_source(failed_record):
 failed_record.update(status='timeout',results=[],message='Worker deadline exceeded')
 executions.save(executions.directory(failed_record['execution_id']),failed_record)
 finding=analyze(DefectRequest(execution_id=failed_record['execution_id']))['findings'][0]
 assert finding['observed']['classification']=='timeout'
 assert finding['sources'][0]['source_id']=='EXEC-'+failed_record['execution_id']

def test_passed_and_running_executions_rejected(failed_record):
 for status in ['passed','running']:
  with patch('app.agents.defect_analysis.get',return_value=failed_record|{'status':status,'results':[]}):
   with pytest.raises(ValueError):analyze(DefectRequest(execution_id=failed_record['execution_id']))

def test_invented_llm_citation_rejected(failed_record):
 finding=LLMFinding(title='Draft',hypotheses=[{'text':'Possible cause','citation_ids':['FAKE-999'],'confidence':'low'}],next_steps=['Investigate'])
 with patch('app.agents.defect_analysis.structured_call',return_value=finding):
  with pytest.raises(ValueError,match='citation'):analyze(DefectRequest(execution_id=failed_record['execution_id'],mode='llm'))

def test_valid_llm_citations_remain_draft(failed_record):
 direct='LOG-'+failed_record['execution_id']+'-0@execution-v1#0'
 finding=LLMFinding(title='Coupon investigation',hypotheses=[{'text':'Expiry guard may differ from contract','citation_ids':[direct],'confidence':'low'}],next_steps=['Inspect guard'])
 with patch('app.agents.defect_analysis.structured_call',return_value=finding):
  result=analyze(DefectRequest(execution_id=failed_record['execution_id'],mode='llm'))
 assert result['findings'][0]['review_status']=='draft'

def test_provider_embedding_shape_validation(monkeypatch):
 monkeypatch.setenv('QA_EMBEDDING_MODE','provider');monkeypatch.setenv('QA_EMBEDDING_BASE_URL','https://example.invalid/v1');monkeypatch.setenv('QA_EMBEDDING_MODEL','mock-embedding');monkeypatch.setenv('QA_EMBEDDING_API_KEY','private')
 response=MagicMock();response.json.return_value={'data':[{'index':0,'embedding':[1.,0.]}]}
 with patch('app.rag.embeddings.httpx.Client') as factory:
  factory.return_value.__enter__.return_value.post.return_value=response
  assert Embedder().embed(['text'])==[[1.,0.]]
  with pytest.raises(ValueError):Embedder().embed(['text','second'])

def test_embedding_space_identity_changes(monkeypatch):
 demo=Embedder().identity
 monkeypatch.setenv('QA_EMBEDDING_MODE','provider');monkeypatch.setenv('QA_EMBEDDING_BASE_URL','https://example.invalid/v1');monkeypatch.setenv('QA_EMBEDDING_MODEL','model');monkeypatch.setenv('QA_EMBEDDING_API_KEY','private')
 assert Embedder().identity!=demo

def test_unknown_embedding_mode_fails(monkeypatch):
 monkeypatch.setenv('QA_EMBEDDING_MODE','typo')
 with pytest.raises(ValueError):Embedder()

def test_unapproved_workflow_not_ingested():
 with pytest.raises(ValueError):ingest_workflow({'status':'rejected'})

def test_api_search_impact_and_status():
 client=TestClient(app)
 assert client.get('/knowledge/status').status_code==200
 assert client.post('/knowledge/search',json={'query':'coupon expiry'}).json()['sources']
 assert client.post('/intelligence/impact',json={'query':'coupon discount'}).status_code==200
 assert client.post('/knowledge/search',json={'query':' '}).status_code==422

def test_api_draft_export_is_local_and_bounded(tmp_path,monkeypatch,failed_record):
 from app.api import defects
 monkeypatch.setattr(defects,'REPORTS',tmp_path/'drafts')
 client=TestClient(app)
 report=client.post('/intelligence/defects',json={'execution_id':failed_record['execution_id']})
 assert report.status_code==200,report.text
 key=report.json()['report_id']
 assert client.get('/intelligence/defects').json()[0]['report_id']==key
 assert client.get('/intelligence/defects/'+key+'/export').status_code==200
 assert client.get('/intelligence/defects/not-a-uuid/export').status_code==404

def test_labeled_retrieval_report():
 from app.evaluate_rag import evaluate
 report=evaluate()
 assert report['queries']==12 and 0<=report['mean_recall_at_5']<=1
 assert 0<=report['mean_precision_at_5']<=1 and report['source_reference_percent']==100
