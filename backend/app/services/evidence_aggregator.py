import hashlib,json
from datetime import datetime,timezone
from uuid import UUID
from . import execution_service as executions
from .suite_registry import ROOT,REGISTRY,context_fingerprint
from ..models.release import ReleaseEvidence

POLICY_FILE=ROOT/'data/release/policy.json'
MANIFEST_FILE=ROOT/'data/release/commerce-v1.json'
REVIEWS=ROOT/'reports/release_readiness/reviews'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def reference(id,kind,path):
 return {'id':id,'kind':kind,'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path)}
def load_review(key):
 path=REVIEWS/(str(UUID(key))+'.json')
 if not path.is_file():raise KeyError(key)
 return json.loads(path.read_text(encoding='utf-8')),path
def stamp(record):
 try:
  value=datetime.fromisoformat(record['completed_at'].replace('Z','+00:00'))
  return value.timestamp() if value.tzinfo else 0
 except (KeyError,TypeError,ValueError):return 0

def gather(request):
 policy=json.loads(POLICY_FILE.read_text(encoding='utf-8'));manifest=json.loads(MANIFEST_FILE.read_text(encoding='utf-8'))
 sources=[reference('policy:'+policy['version'],'policy',POLICY_FILE),reference('manifest:'+manifest['version'],'coverage_manifest',MANIFEST_FILE)]
 records=[];latest={};source_fingerprint=context_fingerprint()
 for key in request.execution_ids:
  record=executions.get(key)
  if record['environment']!='local':raise ValueError('Release scope is the local commerce contract')
  if any(suite not in REGISTRY for suite in record['test_ids']):raise ValueError('Unknown execution registry ID')
  row_counts={status:sum(row['status']==status for row in record['results']) for status in ['passed','failed','error','skipped']}
  if any(record.get(field,0)!=row_counts[status] for field,status in [('passed','passed'),('failed','failed'),('errors','error'),('skipped','skipped')]):
   raise ValueError('Saved execution counts do not match its test results')
  records.append(record);sources.append(reference('execution:'+record['execution_id'],'execution',executions.directory(key)/'record.json'))
  for suite in record['test_ids']:
   current=latest.get(suite)
   if current is None or stamp(record)>stamp(current):latest[suite]=record
 counts={'passed':0,'failed':0,'error':0,'skipped':0,'blocked':0};covered=set()
 used=[]
 for suite,record in latest.items():
  # Names can repeat between API and UI; tuple identity prevents collapsing them.
  expected={(node.split('::')[1],'UI' if '/ui/' in node else 'API') for node in REGISTRY[suite]['nodes']}
  rows=[row for row in record['results'] if row['test_id']==suite]
  if len({(row['name'],row['type']) for row in rows})!=len(rows):raise ValueError('Duplicate test outcomes in saved execution')
  if any((row['name'],row['type']) not in expected or row['status'] not in counts for row in rows):raise ValueError('Unregistered test outcome')
  for row in rows:counts[row['status']]+=1
  missing=len(expected)-len(rows);counts['blocked']+=missing
  if not missing and all(row['status'] in ['passed','failed'] for row in rows):covered.add(suite)
  used.append(record['execution_id'])
 complete=bool(records) and all(record['status'] in ['passed','failed'] for record in records) and not counts['error'] and not counts['blocked']
 percentage=100*sum(all(suite in covered for suite in item['suite_ids']) for item in manifest['requirements'])/len(manifest['requirements']) if records else None
 timestamps=[record.get('completed_at') for record in records]
 oldest=min(records,key=stamp).get('completed_at') if records and all(stamp(record)>0 for record in records) else None
 review=None
 if request.review_id:
  review,path=load_review(request.review_id)
  if review['release_id']!=request.release_id:raise ValueError('Evidence review belongs to another release')
  sources.append(reference('review:'+review['review_id'],'authorized_defect_risk_review',path))
  for key in sorted(set(review.get('reviewed_draft_ids',[])+[item['source_draft_id'] for item in review['defects'] if item.get('source_draft_id')])):
   draft_path=ROOT/'reports/intelligence'/(str(UUID(key))+'.json')
   if not draft_path.is_file():raise KeyError(key)
   sources.append(reference('draft:'+key,'supporting_defect_draft',draft_path))
 defects=review['defects'] if review else []
 evidence=ReleaseEvidence(release_id=request.release_id,tests_total=sum(counts.values()) if records else None,
  tests_passed=counts['passed'] if records else None,tests_failed=counts['failed'] if records else None,
  tests_errors=counts['error'] if records else None,tests_skipped=counts['skipped'] if records else None,tests_blocked=counts['blocked'] if records else None,
  requirement_coverage=float(percentage) if percentage is not None else None,
  critical_defects_open=sum(item['severity']=='critical' and item['status']=='open' for item in defects) if review else None,
  high_defects_open=sum(item['severity']=='high' and item['status']=='open' for item in defects) if review else None,
  risk_level=review['risk_level'] if review else None,unresolved_regression_risks=review['unresolved_regression_risks'] if review else None,
  oldest_execution_at=oldest,review_at=review.get('reviewed_at') if review else None,
  execution_approved=all(record.get('approved') is True for record in records) if records else None,
  contract_matches=all(record.get('contract_version')==manifest['version'] and record.get('source_fingerprint')==source_fingerprint for record in records) if records else None,
  execution_complete=bool(complete) if records else None,source_ids=[source['id'] for source in sources])
 return {'evidence':evidence.model_dump(),'policy':policy,'sources':sources,'suite_fingerprint':source_fingerprint,'coverage_definition':manifest['coverage_definition'],
  'aggregation_note':'Latest completed outcome per registered suite; repeated executions are not double-counted. Missing selected results count as blocked. Older records without explicit timestamps/provenance cannot pass readiness.'}
