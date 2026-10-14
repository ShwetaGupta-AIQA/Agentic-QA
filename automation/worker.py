"""Owned local SUT + fixed pytest subprocess; never executes generated code."""
import argparse,json,os,socket,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
import httpx
from backend.app.services.suite_registry import REGISTRY,ROOT,resolve

def classify(node):
 if node.tag=='error':return 'infrastructure_error'
 text=(node.get('message','')+' '+(node.text or ''))
 return 'product_assertion' if 'AssertionError' in text or 'assert ' in text else 'test_script_error'

def parse_junit(path,selected):
 lookup={}
 for suite in selected:
  for node in REGISTRY[suite]['nodes']:
   lookup[('ui' if '/ui/' in node else 'api',node.split('::')[1])]=suite
 results=[]
 for case in ET.parse(path).getroot().iter('testcase'):
  kind='ui' if 'ui.test_ecommerce' in case.get('classname','') else 'api'
  failure=case.find('failure');error=case.find('error');skip=case.find('skipped')
  issue=failure if failure is not None else error
  status='failed' if failure is not None else 'error' if error is not None else 'skipped' if skip is not None else 'passed'
  results.append({'test_id':lookup.get((kind,case.get('name')),'unmapped'), 'name':case.get('name'), 'type':kind.upper(),
    'status':status,'classification':classify(issue) if issue is not None else 'none',
    'message':(issue.get('message','') if issue is not None else '')[:4000], 'duration_seconds':float(case.get('time','0'))})
 return results

def run(execution_id,ids,verify_defect=False):
 nodes=resolve(ids)
 directory=ROOT/'reports'/'executions'/execution_id;directory.mkdir(parents=True,exist_ok=True)
 evidence=directory/'evidence';evidence.mkdir(exist_ok=True)
 with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
 log=(directory/'sut.log').open('w',encoding='utf-8')
 sut=subprocess.Popen([sys.executable,'-m','uvicorn','sut.ecommerce.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 start=time.monotonic()
 try:
  url=f'http://127.0.0.1:{port}'
  for attempt in range(100):
   if sut.poll() is not None:raise RuntimeError('Local SUT failed to start')
   try:
    if httpx.get(url+'/health',timeout=.5).status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.1)
  else:raise RuntimeError('Local SUT startup timeout')
  env=os.environ.copy();env.update(QA_SUT_URL=url,QA_EVIDENCE_DIR=str(evidence),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',QA_VERIFY_DEFECT='1' if verify_defect else '0')
  command=[sys.executable,'-m','pytest','-c',str(ROOT/'automation/pytest.ini'),'-q','--junitxml='+str(directory/'junit.xml'),*nodes]
  with (directory/'pytest.log').open('w',encoding='utf-8') as output:
   return_code=subprocess.call(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,shell=False)
  results=parse_junit(directory/'junit.xml',ids)
  failed=sum(row['status']=='failed' for row in results);errors=sum(row['status']=='error' for row in results);skipped=sum(row['status']=='skipped' for row in results)
  complete=len(results)==len(nodes) and all(row['test_id']!='unmapped' for row in results)
  status='error' if errors or skipped or not complete or return_code not in (0,1) else 'failed' if failed else 'passed'
  return {'execution_id':execution_id,'test_ids':ids,'environment':'local','status':status,
    'passed':sum(row['status']=='passed' for row in results),'failed':failed,'errors':errors,'skipped':skipped,
    'results':results,'duration_seconds':round(time.monotonic()-start,3),'message':'Assertions are observations, not confirmed defects.'}
 finally:
  sut.terminate()
  try:sut.wait(timeout=5)
  except subprocess.TimeoutExpired:sut.kill();sut.wait()
  log.close()

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('execution_id');parser.add_argument('test_ids',nargs='+');parser.add_argument('--verify-defect',action='store_true');args=parser.parse_args()
 from uuid import UUID
 UUID(args.execution_id)
 directory=ROOT/'reports'/'executions'/args.execution_id
 try:result=run(args.execution_id,args.test_ids,args.verify_defect)
 except Exception as exc:
  result={'execution_id':args.execution_id,'test_ids':args.test_ids,'environment':'local','status':'error','message':'Worker infrastructure failed: '+type(exc).__name__,'results':[]}
 directory.mkdir(parents=True,exist_ok=True);(directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
