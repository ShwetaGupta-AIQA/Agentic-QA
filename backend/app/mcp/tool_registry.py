import hashlib,hmac,json,os
from uuid import UUID
from pathlib import Path
from ..services.suite_registry import ROOT
from ..services import patch_service
from ..services.repair_validator import VALIDATION_ROOT
SCOPES={'get_execution':'executions:read','read_artifact':'artifacts:read','inspect_approved_dom':'healing:read','get_defect_report':'defects:read'}
def authorize(token,tool):
 expected=os.getenv('QA_MCP_SESSION_TOKEN','')
 if len(expected)<32 or not hmac.compare_digest(token,expected):raise PermissionError('Invalid local session capability')
 allowed=set(os.getenv('QA_MCP_SCOPES','').split(','))
 if tool not in SCOPES or SCOPES[tool] not in allowed:raise PermissionError('Tool scope denied')
def execution_record(key):
 key=str(UUID(key));path=ROOT/'reports/executions'/key/'record.json'
 if not path.is_file():raise ValueError('Unknown execution')
 # Read-only: do not reinterpret the parent API process active-job state.
 return json.loads(path.read_text(encoding='utf-8'))
def get_execution(token,execution_id):
 authorize(token,'get_execution');return execution_record(execution_id)
def read_artifact(token,execution_id,artifact_name):
 authorize(token,'read_artifact');record=execution_record(execution_id)
 if artifact_name not in record.get('artifacts',[]):raise ValueError('Artifact not authorized for this execution')
 base=(ROOT/'reports/executions'/str(UUID(execution_id))).resolve();path=(base/artifact_name).resolve()
 if not path.is_relative_to(base) or not path.is_file():raise ValueError('Artifact outside authorized directory')
 data=path.read_bytes()
 result={'execution_id':execution_id,'artifact':artifact_name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
 if path.suffix.lower() in ['.json','.xml','.log','.html','.txt']:
  result.update(text=data[:20000].decode('utf-8',errors='replace'),truncated=len(data)>20000)
 else:result['note']='Binary artifact; use the authenticated local application download path'
 return result
def inspect_approved_dom(token,proposal_id):
 authorize(token,'inspect_approved_dom');record=patch_service.load(proposal_id)
 key=str(UUID(record['baseline']['validation_id']));path=VALIDATION_ROOT/key/'evidence/test_coupon_locator/dom.json'
 if not path.is_file():raise ValueError('No captured DOM evidence available')
 return {'proposal_id':proposal_id,'source':'captured isolated local commerce SUT, not a caller URL','dom':json.loads(path.read_text(encoding='utf-8'))}
def get_defect_report(token,report_id):
 authorize(token,'get_defect_report');path=ROOT/'reports/intelligence'/(str(UUID(report_id))+'.json')
 if not path.is_file():raise ValueError('Unknown defect draft')
 return json.loads(path.read_text(encoding='utf-8'))
