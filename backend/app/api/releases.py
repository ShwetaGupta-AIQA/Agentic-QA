import json,os
from fastapi import APIRouter,HTTPException,Header
from fastapi.responses import FileResponse
from ..models.release import ReleaseRequest,EvidenceReview,ReleaseDecision
from ..services import release_service as service
from ..services.release_auth import authorize,reviewer
from ..services.evidence_aggregator import POLICY_FILE
router=APIRouter()
def auth(header,name):
 try:authorize(header,name)
 except PermissionError:raise HTTPException(403,detail='Configured release reviewer credential and identity are required')
def invoke(fn,*args):
 try:return fn(*args)
 except KeyError:raise HTTPException(404,detail='Unknown release evidence record')
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
 except RuntimeError as exc:raise HTTPException(409,detail=str(exc))
@router.get('/releases/policy')
def policy():return json.loads(POLICY_FILE.read_text(encoding='utf-8'))
@router.get('/releases/reviewer')
def configured_reviewer():return {'reviewer':reviewer(),'configured':len(os.getenv('QA_RELEASE_REVIEW_TOKEN',''))>=32,'scope':'Local evidence attestation and release decision; no deployment'}
@router.post('/releases/evidence-review')
def review(body:EvidenceReview,authorization:str|None=Header(default=None)):
 auth(authorization,body.reviewer);return invoke(service.store_review,body)
@router.get('/releases/evidence-review')
def reviews():
 if not service.REVIEWS.exists():return []
 return [json.loads(file.read_text(encoding='utf-8')) for file in sorted(service.REVIEWS.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]]
@router.post('/releases')
def assess(body:ReleaseRequest):return invoke(service.assess,body)
@router.get('/releases')
def history():
 if not service.REPORTS.exists():return []
 records=[]
 for file in sorted(service.REPORTS.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
  record=json.loads(file.read_text(encoding='utf-8'));record['approval_available']=service.agent.available(record['assessment_id']);records.append(record)
 return records
@router.get('/releases/{key}')
def get(key:str):
 record=invoke(service.load,key);record['approval_available']=service.agent.available(key);return record
@router.post('/releases/{key}/decision')
def decision(key:str,body:ReleaseDecision,authorization:str|None=Header(default=None)):
 auth(authorization,body.reviewer);return invoke(service.decide,key,body)
@router.get('/releases/{key}/export')
def export(key:str):
 invoke(service.load,key);return FileResponse(service.path(key),media_type='application/json',filename='Release_Readiness_Report.json')
