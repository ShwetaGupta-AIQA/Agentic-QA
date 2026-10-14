from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from ..agent import Nonblank

class Document(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 id:Nonblank
 title:Nonblank
 text:str=Field(min_length=1,max_length=100000)
 project:Nonblank='commerce'
 kind:Literal['requirement','test','defect','execution','log']
 source_version:Nonblank
 requirement_id:str=''
 test_id:str=''
 synthetic:bool=True

class SearchRequest(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 query:str=Field(min_length=3,max_length=2000)
 project:str=Field(default='commerce',min_length=1,max_length=100)
 kind:Literal['requirement','test','defect','execution','log']|None=None
 source_version:str|None=Field(default=None,max_length=100)
 top_k:int=Field(default=5,ge=1,le=10)

class DefectRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 execution_id:str
 mode:Literal['demo','llm']='demo'

class Hypothesis(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 text:Nonblank
 citation_ids:list[Nonblank]=Field(min_length=1)
 confidence:Literal['low','medium']='low'

class LLMFinding(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 title:Nonblank
 hypotheses:list[Hypothesis]=Field(min_length=1,max_length=5)
 next_steps:list[Nonblank]=Field(min_length=1,max_length=10)
