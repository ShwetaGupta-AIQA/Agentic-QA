from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from ..models.execution import AutomationRequest,ExecutionResult
from ..services import execution_service as service
from ..services.suite_registry import catalog

router=APIRouter()
@router.get('/automation/suites')
def suites():return catalog()
@router.post('/executions',response_model=ExecutionResult,status_code=202)
def create(body:AutomationRequest):
 try:return service.submit(body)
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
 except RuntimeError as exc:raise HTTPException(429,detail=str(exc))
@router.get('/executions',response_model=list[ExecutionResult])
def history():return service.list_runs()
@router.get('/executions/{execution_id}',response_model=ExecutionResult)
def get(execution_id:str):
 try:return service.get(execution_id)
 except (KeyError,ValueError):raise HTTPException(404,detail='Unknown execution')
@router.get('/executions/{execution_id}/artifacts/{name:path}')
def artifact(execution_id:str,name:str):
 try:return FileResponse(service.artifact(execution_id,name),filename=name.split('/')[-1])
 except (KeyError,ValueError):raise HTTPException(404,detail='Unknown execution artifact')
