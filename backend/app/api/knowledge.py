from fastapi import APIRouter,HTTPException
from ..models.intelligence import SearchRequest
from ..rag.ingestion import ingest_demo,ingest_execution,ingest_workflow
from ..rag.vector_store import collection
from ..services.execution_service import get
from ..workflow import snapshot
from ..orchestration.intelligence_graph import run
router=APIRouter()
@router.get('/knowledge/status')
def status():
 try:
  store,embedder=collection()
  return {'indexed_chunks':store.count(),'embedding_mode':embedder.mode,'embedding_model':embedder.model}
 except Exception:raise HTTPException(503,detail='Knowledge store or embedding configuration is unavailable')
@router.post('/knowledge/ingest/demo')
def demo():
 try:return ingest_demo()
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
 except Exception:raise HTTPException(503,detail='Knowledge ingestion failed; inspect local configuration')
@router.post('/knowledge/ingest/executions/{execution_id}')
def execution(execution_id:str):
 try:return ingest_execution(get(execution_id))
 except KeyError:raise HTTPException(404,detail='Unknown execution')
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
@router.post('/knowledge/ingest/workflows/{run_id}')
def workflow(run_id:str):
 try:return ingest_workflow(snapshot(run_id))
 except KeyError:raise HTTPException(404,detail='Unknown workflow')
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
@router.post('/knowledge/search')
def search(body:SearchRequest):
 try:return run('search',body)
 except Exception:raise HTTPException(503,detail='Knowledge retrieval failed; check embedding configuration')
@router.post('/intelligence/impact')
def impact(body:SearchRequest):
 try:return run('impact',body)
 except Exception:raise HTTPException(503,detail='Impact retrieval failed; check embedding configuration')
