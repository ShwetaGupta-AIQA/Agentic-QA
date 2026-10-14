from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from dotenv import load_dotenv
from pathlib import Path
from .agent import AgentResult
from .models.test_cases import TestCase, Criterion, CaseEdit
from .models.test_data import TestData, DataEdit
from fastapi.responses import Response
import json

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
from .analyzer import analyze
from .workflow import start, snapshot, decide, edit_case, edit_data

from contextlib import asynccontextmanager
from .runtime import load_secrets,validate
from .middleware import AccessTelemetryMiddleware
from . import persistence
@asynccontextmanager
async def lifespan(app):
    load_secrets();validate()
    if __import__('os').getenv('QA_DATABASE_URL'):
        persistence.saver()
        from .services import job_queue
        job_queue.setup()
    yield
    persistence.close()
app = FastAPI(title='Agentic QA Platform', version='0.8.0',lifespan=lifespan)
app.add_middleware(AccessTelemetryMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:5174','http://127.0.0.1:5174'], allow_credentials=False, allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type','Authorization'])

class RequirementRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    requirement: str = Field(min_length=10, max_length=5000)

class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approve', 'reject']

class WorkflowResponse(BaseModel):
    run_id: str
    requirement: str
    analysis: AgentResult | None = None
    mode: Literal['demo', 'llm'] | None = None
    status: Literal['awaiting_approval', 'approved', 'rejected', 'failed']
    decision: Literal['approve', 'reject'] | None = None
    phase: str = 'requirements_review'
    criteria: list[Criterion] = []
    test_cases: list[TestCase] = []
    test_data: list[TestData] = []
    metrics: dict = {}
    errors: list[dict] = []

@app.get('/health')
def health():
    return {'status':'ok','service':'agentic-qa-api'}

@app.post('/requirements/analyze')
def baseline(body: RequirementRequest):
    return analyze(body.requirement)

@app.post('/workflows', response_model=WorkflowResponse)
def create_workflow(body: RequirementRequest):
    try:
        result = start(body.requirement)
        if result.get('phase') == 'failed':
            raise HTTPException(502, detail={'message': 'Requirements Agent failed. Inspect the workflow for its recorded failure.', 'run_id': result['run_id']})
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, detail=f'Agent execution failed: {type(exc).__name__}') from exc

@app.get('/workflows/{run_id}', response_model=WorkflowResponse)
def get_workflow(run_id: str):
    try:
        return snapshot(run_id)
    except KeyError:
        raise HTTPException(404, detail='Unknown run')

@app.post('/workflows/{run_id}/decision', response_model=WorkflowResponse)
def decide_workflow(run_id: str, body: DecisionRequest):
    try:
        return decide(run_id, body.decision)
    except KeyError:
        raise HTTPException(404, detail='Unknown run')
    except RuntimeError as exc:
        raise HTTPException(409, detail=str(exc))

@app.get('/workflows/{run_id}/artifact', response_model=WorkflowResponse)
def approved_artifact(run_id: str):
    result = get_workflow(run_id)
    if result['status'] != 'approved':
        raise HTTPException(409, detail='Only approved analysis is available for test design')
    return result


def test_package(run_id):
    result = get_workflow(run_id)
    if result.get('phase') != 'ready_for_review':
        raise HTTPException(409, detail='A complete test package is not available')
    return result

@app.get('/workflows/{run_id}/test-cases', response_model=list[TestCase])
def get_test_cases(run_id: str):
    return test_package(run_id)['test_cases']

@app.get('/workflows/{run_id}/test-data', response_model=list[TestData])
def get_test_data(run_id: str):
    return test_package(run_id)['test_data']

@app.patch('/workflows/{run_id}/test-cases/{case_id}', response_model=WorkflowResponse)
def update_test_case(run_id: str, case_id: str, body: CaseEdit):
    try:
        return edit_case(run_id, case_id, body)
    except KeyError:
        raise HTTPException(404, detail='Unknown run or test case')
    except RuntimeError as exc:
        raise HTTPException(409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))

@app.get('/workflows/{run_id}/export')
def export_package(run_id: str):
    result = WorkflowResponse.model_validate(test_package(run_id)).model_dump()
    return Response(json.dumps(result, indent=2), media_type='application/json',
        headers={'Content-Disposition': 'attachment; filename="Agentic_QA_Test_Package.json"'})


@app.patch('/workflows/{run_id}/test-data/{data_id}', response_model=WorkflowResponse)
def update_test_data(run_id: str, data_id: str, body: DataEdit):
    try:
        return edit_data(run_id, data_id, body)
    except KeyError:
        raise HTTPException(404, detail='Unknown run or dataset')
    except RuntimeError as exc:
        raise HTTPException(409, detail=str(exc))
    except ValueError:
        raise HTTPException(422, detail='Invalid synthetic fixture or linked test case still requires review')


@app.get('/evaluation/design_benchmark')
def design_benchmark_evaluation_report():
    report = Path(__file__).resolve().parents[1] / 'data' / 'evaluation-summary.json'
    if not report.exists():
        raise HTTPException(404, detail='Run the labeled Test design evaluation first')
    return json.loads(report.read_text(encoding='utf-8'))

from .api.executions import router as execution_router
app.include_router(execution_router)

from .api.knowledge import router as knowledge_router
from .api.defects import router as defect_router
app.include_router(knowledge_router)
app.include_router(defect_router)


@app.get('/evaluation/retrieval')
def rag_evaluation():
 report=Path(__file__).resolve().parents[1]/'data/retrieval-summary.json'
 if not report.exists():raise HTTPException(404,detail='Run the labeled RAG evaluation first')
 return json.loads(report.read_text(encoding='utf-8'))

from .api.healing import router as healing_router
app.include_router(healing_router)

from .api.mcp_tools import router as mcp_router
app.include_router(mcp_router)

from .api.releases import router as release_router
app.include_router(release_router)

@app.get('/ready')
def readiness():
    import os
    checks={'checkpoints':'memory-local','knowledge':'local','execution':'local'}
    try:
        if os.getenv('QA_DATABASE_URL'):
            from .services.job_queue import connect
            with connect() as c:c.execute('SELECT 1')
            checks['checkpoints']='postgresql';checks['execution']=os.getenv('QA_EXECUTION_MODE','local')
        if os.getenv('QA_CHROMA_HOST'):
            from .rag.vector_store import client
            client('remote').heartbeat();checks['knowledge']='chroma-service'
        return {'status':'ready','checks':checks}
    except Exception:raise HTTPException(503,detail='A required dependency is unavailable')
@app.get('/metrics')
def metrics():
    from .telemetry import metrics
    return {'scope':'current process metadata counters; no content or credentials','counters':metrics()}
