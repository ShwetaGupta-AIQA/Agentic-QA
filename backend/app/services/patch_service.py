import hashlib,json
from datetime import datetime,timezone
from threading import RLock
from uuid import UUID
from .suite_registry import ROOT
from .locator_analyzer import CANDIDATES
from .repair_validator import VALIDATION_ROOT
LOCATORS=ROOT/'automation/ui/pages/locators.json'
REPORTS=ROOT/'reports/healing/proposals'
LOCK=RLock()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def context_hash():
 files=['automation/ui/test_healing.py','automation/conftest.py','sut/ecommerce/app.py','sut/ecommerce/index.html']
 return hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in files)).hexdigest()
def path(key):return REPORTS/(str(UUID(key))+'.json')
def load(key):
 target=path(key)
 if not target.is_file():raise KeyError(key)
 return json.loads(target.read_text(encoding='utf-8'))
def save(record):
 REPORTS.mkdir(parents=True,exist_ok=True)
 target=path(record['proposal_id']);temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2),encoding='utf-8');temporary.replace(target)
def apply(key,decision):
 with LOCK:
  record=load(key)
  if record['status'] not in ['proposed','validated']:raise RuntimeError('Proposal already decided')
  if decision.decision=='reject':
   record.update(status='rejected',reviewer=decision.reviewer);save(record);return record
  if decision.approved is not True:raise ValueError('Explicit human approval is required')
  if record['status']!='validated' or not record.get('validation',{}).get('passed'):raise RuntimeError('A passing full-test validation is required')
  validation=record['validation']
  if decision.validation_id!=validation['validation_id']:raise RuntimeError('Review the current validation')
  if record.get('context_hash')!=context_hash():raise RuntimeError('Test or SUT context changed; recreate and revalidate the proposal')
  if digest(LOCATORS)!=record['original_hash']:raise RuntimeError('Locator file changed after proposal; create a new proposal')
  validation_path=VALIDATION_ROOT/str(UUID(validation['validation_id']))/'result.json'
  if not validation_path.exists() or digest(validation_path)!=record['validation_hash']:raise RuntimeError('Validation evidence changed or disappeared')
  proposed=record['selected_candidate']
  if proposed not in CANDIDATES:raise ValueError('Candidate is not registered')
  before=LOCATORS.read_text(encoding='utf-8');data=json.loads(before)
  if data.get('coupon')!=record['original_locator']:raise RuntimeError('Original locator no longer matches')
  data['coupon']=CANDIDATES[proposed]
  after=json.dumps(data,indent=2)+'\n'
  record['audit']={'reviewer':decision.reviewer,'before_hash':record['original_hash'],'validation_id':validation['validation_id'],'before':before,'after':after,'scope':'coupon locator only; assertions and business rules unchanged','approved_at':datetime.now(timezone.utc).isoformat()}
  # Prepare an auditable intent record before the atomic locator replacement.
  record['status']='applying';save(record)
  temporary=LOCATORS.with_suffix('.tmp');temporary.write_text(after,encoding='utf-8');temporary.replace(LOCATORS)
  record.update(status='applied',reviewer=decision.reviewer,applied_hash=digest(LOCATORS));save(record)
  return record
