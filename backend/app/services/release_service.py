import hashlib,json
from threading import RLock
from uuid import UUID,uuid4
from datetime import datetime,timezone
from pathlib import Path
from ..models.release import ReleaseEvidence
from .quality_gates import evaluate
from .evidence_aggregator import ROOT,REVIEWS,sha
from .suite_registry import context_fingerprint
from ..agents import release_readiness as agent

REPORTS=ROOT/'reports/release_readiness/assessments'
LOCK=RLock()
def canonical(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def path(key):return REPORTS/(str(UUID(key))+'.json')
def save(record):
 REPORTS.mkdir(parents=True,exist_ok=True);target=path(record['assessment_id']);temporary=target.with_suffix('.tmp')
 temporary.write_text(json.dumps(record,indent=2),encoding='utf-8');temporary.replace(target)
def load(key):
 target=path(key)
 if not target.exists():raise KeyError(key)
 return json.loads(target.read_text(encoding='utf-8'))
def assess(request):
 key=str(uuid4());state=agent.start(request,key)
 record={'assessment_id':key,'release_id':request.release_id,'request':request.model_dump(),'aggregate':state['aggregate'],
   'evaluation':state['evaluation'],'explanation':state['explanation'],'status':'awaiting_review','assessed_at':datetime.now(timezone.utc).isoformat()}
 record['assessment_hash']=canonical({key:record[key] for key in ['request','aggregate','evaluation','explanation','assessed_at']})
 save(record);return record
def store_review(body):
 REVIEWS.mkdir(parents=True,exist_ok=True)
 for key in body.reviewed_draft_ids+ [item.source_draft_id for item in body.defects if item.source_draft_id]:
  if not (ROOT/'reports/intelligence'/(str(UUID(key))+'.json')).is_file():raise KeyError(key)
 key=str(uuid4());record={**body.model_dump(),'review_id':key,'reviewed_at':datetime.now(timezone.utc).isoformat()}
 (REVIEWS/(key+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8');return record
def decide(key,body):
 with LOCK:
  record=load(key)
  if record['status']!='awaiting_review':raise RuntimeError('Assessment already decided')
  if not agent.available(key):raise RuntimeError('Backend checkpoint was restarted; create a fresh assessment')
  if body.assessment_hash!=record['assessment_hash']:raise RuntimeError('Assessment changed; review the current report')
  original=canonical({field:record[field] for field in ['request','aggregate','evaluation','explanation','assessed_at']})
  if original!=record['assessment_hash']:raise RuntimeError('Stored assessment was altered')
  for source in record['aggregate']['sources']:
   location=(ROOT/source['path']).resolve()
   if not location.is_relative_to(ROOT.resolve()) or not location.is_file() or sha(location)!=source['sha256']:
    raise RuntimeError('Source evidence changed; reassess')
  if context_fingerprint()!=record['aggregate']['suite_fingerprint']:raise RuntimeError('Suite or SUT changed; reassess')
  current=evaluate(ReleaseEvidence.model_validate(record['aggregate']['evidence']),record['aggregate']['policy'])
  if current['recommendation']!=record['evaluation']['recommendation'] or any(a['status']!=b['status'] for a,b in zip(current['gates'],record['evaluation']['gates'])):
   raise RuntimeError('Gates changed or evidence expired; create a fresh assessment')
  recommendation=current['recommendation']
  if body.decision!='NO_GO' and recommendation=='NO_GO':raise RuntimeError('Blocking gates cannot be overridden')
  if body.decision=='GO' and recommendation!='GO':raise RuntimeError('Residual risks require conditional authorization')
  if body.decision=='CONDITIONAL_GO' and not body.conditions_acknowledged:raise ValueError('Acknowledge release conditions explicitly')
  audit={**body.model_dump(),'authorized_at':datetime.now(timezone.utc).isoformat(),'scope':'Local release decision record only; no deployment or publication'}
  agent.resume(key,audit);record.update(status='rejected' if body.decision=='NO_GO' else 'authorized',human_decision=audit);save(record);return record
