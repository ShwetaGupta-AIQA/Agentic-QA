import asyncio,json,secrets,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from ..services.execution_service import clean_environment
from ..services.suite_registry import ROOT
from .tool_registry import SCOPES

def validate_arguments(name,args):
 fields={'get_execution':{'execution_id'},'read_artifact':{'execution_id','artifact_name'},'inspect_approved_dom':{'proposal_id'},'get_defect_report':{'report_id'}}
 if name not in fields or set(args)!=fields[name] or any(not isinstance(value,str) or len(value)>300 for value in args.values()):
  raise ValueError('Unknown MCP tool or invalid arguments')
async def request(name=None,args=None):
 from ..telemetry import emit
 if name is not None:validate_arguments(name,args or {})
 emit('tool_call',tool_name=name if name in SCOPES else 'list_tools')
 token=secrets.token_urlsafe(32);env=clean_environment()
 env.update(QA_MCP_SESSION_TOKEN=token,QA_MCP_SCOPES=','.join(SCOPES.values()))
 parameters=StdioServerParameters(command=sys.executable,args=['-m','app.mcp.server'],env=env,cwd=str(ROOT/'backend'))
 async with asyncio.timeout(25):
  async with stdio_client(parameters) as (reader,writer):
   async with ClientSession(reader,writer) as session:
    await session.initialize()
    if name is None:
     result=await session.list_tools();resources=await session.list_resources()
     listed=[]
     for tool in result.tools:
      schema=dict(tool.inputSchema);schema['properties']={key:value for key,value in schema.get('properties',{}).items() if key!='token'}
      schema['required']=[key for key in schema.get('required',[]) if key!='token']
      listed.append({'name':tool.name,'description':tool.description,'input_schema':schema,'scope':SCOPES[tool.name]})
     return {'tools':listed,'resources':[str(resource.uri) for resource in resources.resources],'transport':'private stdio','authentication':'per-session capability injected by the backend','patch_tools':False}
    result=await session.call_tool(name,arguments={**args,'token':token})
    if result.isError:raise ValueError('MCP server rejected the request')
    if result.structuredContent is not None:return result.structuredContent
    return json.loads(result.content[0].text)
if __name__=='__main__':print(json.dumps(asyncio.run(request()),indent=2))
