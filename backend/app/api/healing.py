import json
from uuid import UUID
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from ..models.healing import CandidateRequest,HealingDecision
from ..agents.self_healing import demonstrate,validate_proposal,apply_and_regress
from ..services import patch_service as patches
from ..services.repair_validator import VALIDATION_ROOT
router=APIRouter()
def invoke(fn,*args):
 try:return fn(*args)
 except KeyError:raise HTTPException(404,detail='Unknown healing record')
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
 except RuntimeError as exc:raise HTTPException(409,detail=str(exc))
@router.post('/healing/demonstration')
def start():return invoke(demonstrate)
@router.get('/healing')
def history():
 if not patches.REPORTS.exists():return []
 return [json.loads(path.read_text(encoding='utf-8')) for path in sorted(patches.REPORTS.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]]
@router.get('/healing/{key}')
def get(key:str):return invoke(patches.load,key)
@router.post('/healing/{key}/validate')
def check(key:str,body:CandidateRequest):return invoke(validate_proposal,key,body.candidate)
@router.post('/healing/{key}/decision')
def decide(key:str,body:HealingDecision):return invoke(apply_and_regress,key,body)
@router.get('/healing/{key}/evidence/{validation_id}/{name:path}')
def artifact(key:str,validation_id:str,name:str):
 record=invoke(patches.load,key)
 ids={record['baseline']['validation_id'],record.get('validation',{}).get('validation_id'),record.get('regression',{}).get('validation_id')}
 if validation_id not in ids:raise HTTPException(404,detail='Evidence is not linked to this proposal')
 base=VALIDATION_ROOT/str(UUID(validation_id));candidate=(base/name).resolve()
 if not candidate.is_relative_to(base.resolve()) or not candidate.is_file() or candidate.suffix not in ['.json','.xml','.log','.html','.png','.zip']:
  raise HTTPException(404,detail='Unknown evidence artifact')
 return FileResponse(candidate,filename=candidate.name)
