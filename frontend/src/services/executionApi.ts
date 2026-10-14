export type Suite={id:string;title:string;types:string[];automation_count:number;contract_version:string};
export type Execution={execution_id:string;status:string;test_ids:string[];passed:number;failed:number;errors:number;skipped:number;duration_seconds:number;message:string;results:{test_id:string;name:string;type:string;status:string;classification:string;message:string}[];artifacts:string[]};
const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
async function json<T>(path:string,options?:RequestInit):Promise<T>{const response=await fetch(API+path,options);if(!response.ok){const body=await response.json().catch(()=>null);throw new Error(typeof body?.detail==='string'?body.detail:`Execution request failed (${response.status})`);}return response.json();}
export const suites=()=>json<Suite[]>('/automation/suites');
export const history=()=>json<Execution[]>('/executions');
export const execution=(id:string)=>json<Execution>('/executions/'+encodeURIComponent(id));
export const execute=(test_ids:string[])=>json<Execution>('/executions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({test_ids,environment:'local',approved:true})});
export const artifactUrl=(id:string,path:string)=>API+'/executions/'+encodeURIComponent(id)+'/artifacts/'+path.split('/').map(encodeURIComponent).join('/');
