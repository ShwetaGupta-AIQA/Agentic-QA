from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict
from ..mcp.client import request
router=APIRouter()
class ToolRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 arguments:dict[str,str]
@router.get('/mcp/tools')
async def tools():
 try:return await request()
 except Exception:raise HTTPException(503,detail='Local MCP session unavailable')
@router.post('/mcp/tools/{name}')
async def invoke(name:str,body:ToolRequest):
 try:return await request(name,body.arguments)
 except ValueError as exc:raise HTTPException(422,detail=str(exc))
 except Exception:raise HTTPException(503,detail='MCP tool failed or scope was denied')
