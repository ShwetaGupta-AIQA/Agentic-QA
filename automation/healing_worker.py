import argparse,json,os,socket,subprocess,sys,time
from pathlib import Path
from uuid import UUID
import xml.etree.ElementTree as ET
import httpx
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'baseline','role_coupon','testid_coupon'}
def run(run_id,candidate):
 if candidate not in ALLOWED:raise ValueError('Unknown candidate')
 path=ROOT/'reports/healing/validation'/str(UUID(run_id));path.mkdir(parents=True,exist_ok=True)
 evidence=path/'evidence';evidence.mkdir(exist_ok=True)
 with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
 with (path/'sut.log').open('w',encoding='utf-8') as log:
  sut=subprocess.Popen([sys.executable,'-m','uvicorn','sut.ecommerce.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  try:
   url=f'http://127.0.0.1:{port}'
   for attempt in range(100):
    try:
     if httpx.get(url+'/health',timeout=.3).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.1)
   else:raise RuntimeError('SUT not ready')
   env=os.environ.copy();env.update(QA_SUT_URL=url,QA_EVIDENCE_DIR=str(evidence),QA_HEALING_CANDIDATE='' if candidate=='baseline' else candidate,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',QA_VERIFY_DEFECT='0')
   with (path/'pytest.log').open('w',encoding='utf-8') as output:
    return_code=subprocess.call([sys.executable,'-m','pytest','-c',str(ROOT/'automation/pytest.ini'),'-q','--junitxml='+str(path/'junit.xml'),'automation/ui/test_healing.py::test_coupon_locator'],cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,shell=False)
   cases=list(ET.parse(path/'junit.xml').getroot().iter('testcase'))
   passed=return_code==0 and len(cases)==1 and not any(child.tag in ['failure','error','skipped'] for child in cases[0])
   details=evidence/'test_coupon_locator'
   issue=next((child for case in cases for child in case if child.tag in ['failure','error']),None)
   category='passed' if passed else 'infrastructure_error' if issue is not None and issue.tag=='error' else 'product_assertion' if issue is not None and 'AssertionError' in (issue.get('message','')+(issue.text or '')) else 'test_script_error'
   kind=json.loads((details/'failure-kind.json').read_text()) if (details/'failure-kind.json').exists() else {'category':category,'intent':'apply_coupon'}
   locator=json.loads((details/'locator-check.json').read_text()) if (details/'locator-check.json').exists() else {}
   result={'validation_id':run_id,'candidate':candidate,'passed':passed,'category':kind['category'],'matches':locator.get('matches'), 'full_test':'test_coupon_locator','expected_payable':'900.00','patch_applied':False}
   (path/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
  finally:
   sut.terminate()
   try:sut.wait(timeout=5)
   except subprocess.TimeoutExpired:sut.kill();sut.wait()
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('run_id');parser.add_argument('candidate',choices=sorted(ALLOWED));args=parser.parse_args()
 try:run(args.run_id,args.candidate)
 except Exception:
  path=ROOT/'reports/healing/validation'/str(UUID(args.run_id));path.mkdir(parents=True,exist_ok=True);(path/'result.json').write_text(json.dumps({'validation_id':args.run_id,'candidate':args.candidate,'passed':False,'category':'infrastructure_error','patch_applied':False}),encoding='utf-8')
