from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
class CandidateRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 candidate:Literal['role_coupon','testid_coupon']
class HealingDecision(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,strict=True)
 decision:Literal['approve','reject']
 reviewer:str=Field(min_length=2,max_length=100)
 validation_id:str
 approved:bool=False
