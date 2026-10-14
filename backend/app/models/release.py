from datetime import datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from ..agent import Nonblank

class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,str_strip_whitespace=True)
class ConfirmedDefect(Strict):
 id:Nonblank
 severity:Literal['critical','high','medium','low']
 status:Literal['open','resolved']
 source_draft_id:str|None=None

class EvidenceReview(Strict):
 release_id:str=Field(min_length=1,max_length=100)
 reviewer:str=Field(min_length=2,max_length=100)
 defects:list[ConfirmedDefect]=Field(max_length=100)
 risk_level:Literal['low','medium','high']
 unresolved_regression_risks:int=Field(ge=0,le=100)
 notes:str=Field(min_length=10,max_length=4000)
 reviewed:bool
 reviewed_draft_ids:list[str]=Field(default_factory=list,max_length=30)
 @model_validator(mode='after')
 def checked(self):
  if not self.reviewed:raise ValueError('Explicit evidence review is required')
  if len({item.id for item in self.defects})!=len(self.defects):raise ValueError('Duplicate confirmed defect IDs')
  return self

class ReleaseRequest(Strict):
 release_id:str=Field(min_length=1,max_length=100)
 execution_ids:list[str]=Field(default_factory=list,max_length=10)
 review_id:str|None=None
 explanation_mode:Literal['demo','llm']='demo'
 @model_validator(mode='after')
 def unique(self):
  if len(set(self.execution_ids))!=len(self.execution_ids):raise ValueError('Duplicate execution IDs')
  return self

class ReleaseEvidence(Strict):
 release_id:Nonblank
 tests_total:int|None=Field(default=None,ge=0)
 tests_passed:int|None=Field(default=None,ge=0)
 tests_failed:int|None=Field(default=None,ge=0)
 tests_errors:int|None=Field(default=None,ge=0)
 tests_skipped:int|None=Field(default=None,ge=0)
 tests_blocked:int|None=Field(default=None,ge=0)
 requirement_coverage:float|None=Field(default=None,ge=0,le=100)
 critical_defects_open:int|None=Field(default=None,ge=0)
 high_defects_open:int|None=Field(default=None,ge=0)
 risk_level:Literal['low','medium','high']|None=None
 unresolved_regression_risks:int|None=Field(default=None,ge=0)
 oldest_execution_at:str|None=None
 review_at:str|None=None
 execution_approved:bool|None=None
 contract_matches:bool|None=None
 execution_complete:bool|None=None
 source_ids:list[str]=Field(default_factory=list)
 @model_validator(mode='after')
 def consistent(self):
  counts=[self.tests_passed,self.tests_failed,self.tests_errors,self.tests_skipped,self.tests_blocked]
  if self.tests_total is not None and all(value is not None for value in counts) and sum(counts)!=self.tests_total:
   raise ValueError('Execution counts do not reconcile')
  return self

class Explanation(Strict):
 summary:Nonblank
 remediations:list[dict[str,str]]=Field(default_factory=list,max_length=30)

class ReleaseDecision(Strict):
 decision:Literal['GO','CONDITIONAL_GO','NO_GO']
 reviewer:str=Field(min_length=2,max_length=100)
 assessment_hash:Nonblank
 reason:str=Field(min_length=10,max_length=4000)
 conditions_acknowledged:bool=False
