from ..telemetry import observe
import json,os,subprocess,sys,time,signal
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from threading import RLock,BoundedSemaphore
from uuid import UUID,uuid4
from pathlib import Path
from ..agents.automation_agent import plan
from .suite_registry import ROOT,context_fingerprint
from ..models.execution import ExecutionResult

REPORT_ROOT=ROOT/'reports'/'executions'
TIMEOUT_SECONDS=180
pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='qa-execution')
slots=BoundedSemaphore(4);lock=RLock();active=set()

def directory(execution_id):
 UUID(execution_id)
 return REPORT_ROOT/str(UUID(execution_id))
def save(path,data):
 path.mkdir(parents=True,exist_ok=True)
 temporary=path/'record.tmp';temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(path/'record.json')
def artifacts(path):
 return sorted(str(p.relative_to(path)).replace('\\','/') for p in path.rglob('*') if p.is_file() and p.name not in ['record.json','record.tmp','result.json'])

def stop_tree(process):
 if process.poll() is not None:return
 if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
 else:os.killpg(process.pid,signal.SIGKILL)
 process.wait(timeout=15)

def clean_environment():
 allowed={'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','COMSPEC','PLAYWRIGHT_BROWSERS_PATH'}
 return {key:value for key,value in os.environ.items() if key.upper() in allowed}

@observe('execute')
def execute(execution_id,ids,release_slot=True):
 path=directory(execution_id);started=time.monotonic();record={'execution_id':execution_id,'test_ids':ids,'status':'error','artifacts':[]}
 try:
  with lock:
   record=json.loads((path/'record.json').read_text(encoding='utf-8'));record['status']='running';save(path,record)
  with (path/'worker.log').open('w',encoding='utf-8') as log:
   process=subprocess.Popen([sys.executable,'-m','automation.worker',execution_id,*ids],cwd=ROOT,env=clean_environment(),stdout=log,stderr=subprocess.STDOUT,shell=False,start_new_session=os.name!='nt')
   try:process.wait(timeout=TIMEOUT_SECONDS)
   except subprocess.TimeoutExpired:
    stop_tree(process);record.update(status='timeout',message='Execution exceeded the fixed worker deadline; owned process tree stopped.')
   else:
    result_path=path/'result.json'
    if process.returncode!=0 or not result_path.exists():record.update(status='error',message='Worker did not return a complete result')
    else:record.update(ExecutionResult.model_validate(json.loads(result_path.read_text(encoding='utf-8'))).model_dump(exclude_unset=True))
 except Exception as exc:record.update(status='error',message='Execution infrastructure failure: '+type(exc).__name__)
 finally:
  with lock:
   if record.get('source_fingerprint') and record['source_fingerprint']!=context_fingerprint():record.update(status='error',message='Suite/SUT source changed during execution')
   record['completed_at']=datetime.now(timezone.utc).isoformat();record['duration_seconds']=round(time.monotonic()-started,3);record['artifacts']=artifacts(path);save(path,record);active.discard(execution_id)
  if release_slot:slots.release()

@observe('submit')
def submit(request):
 selection=plan(request)
 if os.getenv('QA_EXECUTION_MODE')=='queue':
  from . import job_queue
  execution_id=str(uuid4());path=directory(execution_id)
  record=ExecutionResult(execution_id=execution_id,status='queued',test_ids=selection['test_ids'],created_at=datetime.now(timezone.utc).isoformat(),approved=True,contract_version='commerce-v1',source_fingerprint=context_fingerprint()).model_dump()
  save(path,record)
  try:job_queue.enqueue(execution_id,selection['test_ids'])
  except Exception:
   record.update(status='error',message='Queue submission failed; explicit rerun required');save(path,record);raise
  return record
 if not slots.acquire(blocking=False):raise RuntimeError('Execution queue is full; try again after a run completes')
 execution_id=str(uuid4());path=directory(execution_id)
 record=ExecutionResult(execution_id=execution_id,status='queued',test_ids=selection['test_ids'],created_at=datetime.now(timezone.utc).isoformat(),approved=True,contract_version='commerce-v1',source_fingerprint=context_fingerprint()).model_dump()
 try:
  with lock:save(path,record);active.add(execution_id)
  pool.submit(execute,execution_id,selection['test_ids'])
 except Exception:
  slots.release();active.discard(execution_id);raise
 return record

def get(execution_id):
 execution_id=str(UUID(execution_id))
 path=directory(execution_id)
 with lock:
  if not (path/'record.json').is_file():raise KeyError(execution_id)
  record=json.loads((path/'record.json').read_text(encoding='utf-8'))
  if record['status'] in ['queued','running'] and os.getenv('QA_EXECUTION_MODE')=='queue':
   from . import job_queue
   state=job_queue.state(execution_id)
   if state in [None,'error','finished']:
    record.update(status='error',message='Worker lease expired or result unavailable; rerun explicitly.');save(path,record)
  elif record['status'] in ['queued','running'] and execution_id not in active:
   record.update(status='error',message='Backend restarted during execution; rerun explicitly.');save(path,record)
  return record

def list_runs():
 if not REPORT_ROOT.exists():return []
 return [get(path.name) for path in sorted(REPORT_ROOT.iterdir(),key=lambda p:p.stat().st_mtime,reverse=True) if (path/'record.json').is_file()][:50]

def artifact(execution_id,name):
 record=get(execution_id)
 if name not in record['artifacts']:raise KeyError(name)
 path=directory(execution_id);candidate=(path/name).resolve()
 if not candidate.is_relative_to(path.resolve()) or not candidate.is_file():raise KeyError(name)
 return candidate
