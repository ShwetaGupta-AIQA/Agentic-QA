import json,os
from mcp.server.fastmcp import FastMCP
from . import tool_registry as tools
mcp=FastMCP('local-qa-read-tools')
@mcp.tool()
def get_execution(token:str,execution_id:str)->dict:
 "Read one authorized UUID execution record without modifying it."
 return tools.get_execution(token,execution_id)
@mcp.tool()
def read_artifact(token:str,execution_id:str,artifact_name:str)->dict:
 "Read only an artifact listed in the authorized execution manifest."
 return tools.read_artifact(token,execution_id,artifact_name)
@mcp.tool()
def inspect_approved_dom(token:str,proposal_id:str)->dict:
 "Inspect saved DOM from the registered isolated coupon healing example; no arbitrary URL."
 return tools.inspect_approved_dom(token,proposal_id)
@mcp.tool()
def get_defect_report(token:str,report_id:str)->dict:
 "Read a persisted local draft by UUID. No publication tool is available."
 return tools.get_defect_report(token,report_id)
@mcp.resource('qa://policy')
def policy()->str:
 return json.dumps({'transport':'private local stdio','tools':list(tools.SCOPES),'mutations':False,'patch_tools':False})
if __name__=='__main__':
 if len(os.getenv('QA_MCP_SESSION_TOKEN',''))<32:raise RuntimeError('Launch through the authenticated local MCP client')
 mcp.run(transport='stdio')
