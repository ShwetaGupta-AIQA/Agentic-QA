from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class AutomationRequest(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 test_ids:list[str]=Field(min_length=1,max_length=10)
 environment:Literal['local']='local'
 approved:Literal[True]

class ExecutionResult(BaseModel):
 execution_id:str
 status:Literal['queued','running','passed','failed','error','timeout']
 test_ids:list[str]
 environment:str='local'
 passed:int=0
 failed:int=0
 errors:int=0
 skipped:int=0
 duration_seconds:float=0
 results:list[dict]=Field(default_factory=list)
 artifacts:list[str]=Field(default_factory=list)
 message:str=''

 created_at:str|None=None
 completed_at:str|None=None
 approved:bool=False
 contract_version:str|None=None
 source_fingerprint:str|None=None
