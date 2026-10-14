"""Authenticated controlled-demo smoke and restart recovery; secrets never printed."""
import argparse,json,time,base64,urllib.request,urllib.error,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8080');parser.add_argument('--restart',action='store_true');args=parser.parse_args()
 login=json.loads((ROOT/'.secrets/demo-login.json').read_text());basic='Basic '+base64.b64encode((login['username']+':'+login['password']).encode()).decode()
 def call(path,body=None,authenticated=True,reviewer_token=None):
  headers={'Authorization':basic} if authenticated else {}
  if reviewer_token:headers['X-QA-Reviewer']='Bearer '+reviewer_token
  if body is not None:headers['Content-Type']='application/json'
  request=urllib.request.Request(args.base_url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  with urllib.request.urlopen(request,timeout=120) as response:
   data=response.read();return json.loads(data) if 'application/json' in response.headers.get('Content-Type','') else data.decode()
 def wait_ready():
  for _ in range(90):
   try:
    result=call('/api/ready')
    if result['status']=='ready':return result
   except (urllib.error.URLError,TimeoutError):pass
   time.sleep(1)
  raise RuntimeError('Dependencies did not become ready')
 try:call('/api/releases',authenticated=False);raise AssertionError('Anonymous API access accepted')
 except urllib.error.HTTPError as exc:assert exc.code==401
 controls=[]
 for path,body in [('/api/executions',{'test_ids':['ECOM-001'],'approved':False}),('/api/executions',{'test_ids':['UNKNOWN'],'approved':True}),('/api/executions',{'test_ids':['ECOM-001']}),('/api/mcp/tools/unknown',{'arguments':{}})]:
  try:call(path,body);raise AssertionError('Unapproved or unknown tool selection accepted')
  except urllib.error.HTTPError as exc:
   assert exc.code==422;controls.append({'path':path,'status':422})
 ready=wait_ready();assert ready['checks']['checkpoints']=='postgresql';assert ready['checks']['knowledge']=='chroma-service';assert ready['checks']['execution']=='queue'
 workflow=call('/api/workflows',{'requirement':'A valid coupon gives ten percent discount during checkout; expired coupons must be rejected.'});assert workflow['status']=='awaiting_approval'
 assessment=call('/api/releases',{'release_id':'deployment-smoke','execution_ids':[]});assert assessment['evaluation']['recommendation']=='NO_GO'
 call('/api/knowledge/ingest/demo',{});knowledge=call('/api/knowledge/status');assert knowledge['indexed_chunks']>0
 if args.restart:
  subprocess.run(['docker','compose','restart','backend','chroma'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
  wait_ready()
  recovered=call('/api/workflows/'+workflow['run_id']);assert recovered['status']=='awaiting_approval'
  release=call('/api/releases/'+assessment['assessment_id']);assert release['approval_available'] is True
  assert call('/api/knowledge/status')['indexed_chunks']==knowledge['indexed_chunks']
 run=call('/api/executions',{'test_ids':['ECOM-%03d'%i for i in range(1,11)],'approved':True,'environment':'local'})
 for _ in range(240):
  execution=call('/api/executions/'+run['execution_id'])
  if execution['status'] not in ['queued','running']:break
  time.sleep(1)
 assert execution['status']=='passed' and execution['passed']==15, 'Isolated commerce execution did not pass'
 final=call('/api/releases',{'release_id':'deployment-verified','execution_ids':[run['execution_id']]});assert final['evaluation']['recommendation']=='NO_GO';assert final['evaluation']['pass_rate']==100
 try:
  call('/api/releases/'+final['assessment_id']+'/decision',{'decision':'GO','reviewer':'local-reviewer','assessment_hash':final['assessment_hash'],'reason':'Credential rejection smoke test'})
  raise AssertionError('Unauthorized approval accepted')
 except urllib.error.HTTPError as exc:assert exc.code==403
 try:
  call('/api/releases/'+final['assessment_id']+'/decision',{'decision':'GO','reviewer':'local-reviewer','assessment_hash':final['assessment_hash'],'reason':'Hard gate enforcement verification'},reviewer_token=(ROOT/'.secrets/reviewer_token').read_text().strip())
  raise AssertionError('Reviewer overrode blocking gates')
 except urllib.error.HTTPError as exc:assert exc.code==409
 exported=call('/api/releases/'+final['assessment_id']+'/export');assert exported['assessment_hash']==final['assessment_hash']
 report=dict(scope='Actual local controlled Docker deployment; no human authorization',approval_control_cases=controls,approval_control_enforced=len(controls),unauthorized_tool_executions_observed=0,anonymous_api_status=401,unauthorized_release_status=403,authenticated_override_status=409,dependencies=ready['checks'],restart_tested=args.restart,workflow_checkpoint_recovered=args.restart,release_interrupt_recovered=args.restart,chroma_chunks=knowledge['indexed_chunks'],isolated_execution_id=run['execution_id'],tests_passed=execution['passed'],tests_failed=execution['failed'],assessment_id=final['assessment_id'],recommendation=final['evaluation']['recommendation'],pass_rate=final['evaluation']['pass_rate'],coverage=final['aggregate']['evidence']['requirement_coverage'],export_hash_matches=True,metrics=call('/api/metrics')['counters'])
 target=ROOT/'reports/deployment-container-verification.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
