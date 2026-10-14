export type Validation={validation_id:string;candidate:string;passed:boolean;category:string;matches?:number;full_test?:string};
export type Proposal={proposal_id:string;status:string;target:string;original_locator:Record<string,string>;original_hash:string;candidates:{id:string;locator:Record<string,string>;matches:number;reason:string}[];baseline:Validation;validation?:Validation;regression?:Validation;selected_candidate?:string;patch_preview?:string;note:string;audit?:{reviewer:string;scope:string;before_hash:string;validation_id:string}};
const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
async function json<T>(path:string,body?:unknown):Promise<T>{const r=await fetch(API+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok){const data=await r.json().catch(()=>null);throw new Error(typeof data?.detail==='string'?data.detail:`Healing request failed (${r.status})`);}return r.json();}
export const history=()=>json<Proposal[]>('/healing');
export const demonstrate=()=>json<Proposal>('/healing/demonstration',{});
export const validate=(id:string,candidate:string)=>json<Proposal>('/healing/'+encodeURIComponent(id)+'/validate',{candidate});
export const decision=(id:string,decision:string,reviewer:string,validation_id:string,approved:boolean)=>json<Proposal>('/healing/'+encodeURIComponent(id)+'/decision',{decision,reviewer,validation_id,approved});
export const evidence=(id:string,validation:string,path:string)=>API+'/healing/'+encodeURIComponent(id)+'/evidence/'+encodeURIComponent(validation)+'/'+path.split('/').map(encodeURIComponent).join('/');
export type MCPInfo={tools:{name:string;description:string;scope:string;input_schema:Record<string,unknown>}[];resources:string[];transport:string;authentication:string;patch_tools:boolean};
export const mcpTools=()=>json<MCPInfo>('/mcp/tools');
export const mcpCall=(tool:string,args:Record<string,string>)=>json<unknown>('/mcp/tools/'+encodeURIComponent(tool),{arguments:args});
