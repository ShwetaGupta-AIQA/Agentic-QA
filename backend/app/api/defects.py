import json
from pathlib import Path
from uuid import UUID,uuid4
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from ..models.intelligence import DefectRequest
from ..orchestration.intelligence_graph import run
from ..rag.vector_store import ROOT
router=APIRouter()
REPORTS=ROOT/'reports/intelligence'
@router.post('/intelligence/defects')
def analyze(body:DefectRequest):
 try:result=run('defect',body)
 except KeyError:raise HTTPException(404,detail='Unknown execution')
 except ValueError as exc:raise HTTPException(422,detail='Invalid request, unavailable evidence or model output')
 except Exception:raise HTTPException(502,detail='Defect analysis failed; inspect local provider configuration')
 report_id=str(uuid4());result['report_id']=report_id
 REPORTS.mkdir(parents=True,exist_ok=True)
 (REPORTS/(report_id+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
 return result
@router.get('/intelligence/defects')
def history():
 if not REPORTS.exists():return []
 return [json.loads(path.read_text(encoding='utf-8')) for path in sorted(REPORTS.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]]
@router.get('/intelligence/defects/{report_id}/export')
def export(report_id:str):
 try:path=REPORTS/(str(UUID(report_id))+'.json')
 except ValueError:raise HTTPException(404,detail='Unknown draft')
 if not path.is_file():raise HTTPException(404,detail='Unknown draft')
 return FileResponse(path,media_type='application/json',filename='Defect_Analysis_Draft.json')
