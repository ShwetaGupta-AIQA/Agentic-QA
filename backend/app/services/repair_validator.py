import json,subprocess,sys
from threading import BoundedSemaphore
from uuid import uuid4
from .suite_registry import ROOT
from .execution_service import clean_environment,stop_tree
VALIDATION_ROOT=ROOT/'reports/healing/validation'
slots=BoundedSemaphore(2)
def validate(candidate,locator_snapshot=None):
 if candidate not in ['baseline','role_coupon','testid_coupon']:raise ValueError('Unknown candidate')
 env=clean_environment()
 if locator_snapshot is not None:
  from .locator_analyzer import CANDIDATES
  if not isinstance(locator_snapshot,dict) or set(locator_snapshot)!= {'coupon'} or locator_snapshot['coupon'] not in list(CANDIDATES.values())+[{'kind':'css','value':'#apply-coupon'}]:
   raise ValueError('Unknown locator snapshot')
  env['QA_HEALING_APPROVED_SNAPSHOT']=json.dumps(locator_snapshot)
 if not slots.acquire(blocking=False):raise RuntimeError('Validation queue is busy')
 key=str(uuid4());path=VALIDATION_ROOT/key;path.mkdir(parents=True)
 try:
  with (path/'worker.log').open('w',encoding='utf-8') as log:
   process=subprocess.Popen([sys.executable,'-m','automation.healing_worker',key,candidate],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,shell=False,start_new_session=sys.platform!='win32')
   try:process.wait(timeout=45)
   except subprocess.TimeoutExpired:
    stop_tree(process);return {'validation_id':key,'candidate':candidate,'passed':False,'category':'timeout','patch_applied':False}
  if process.returncode!=0 or not (path/'result.json').exists():raise RuntimeError('Validation worker failed')
  return json.loads((path/'result.json').read_text(encoding='utf-8'))
 finally:slots.release()
