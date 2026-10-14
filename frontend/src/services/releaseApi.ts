export type Gate={id:string;status:'PASS'|'FAIL'|'UNKNOWN';observed:unknown;policy:string;blocking:boolean;source_ids:string[];remediation:string};
export type Assessment={assessment_id:string;release_id:string;assessment_hash:string;status:string;approval_available?:boolean;
 aggregate:{evidence:{tests_total:number|null;tests_passed:number|null;tests_failed:number|null;tests_errors:number|null;tests_skipped:number|null;tests_blocked:number|null;requirement_coverage:number|null;critical_defects_open:number|null;high_defects_open:number|null;risk_level:string|null};
 sources:{id:string;kind:string;path:string;sha256:string}[];coverage_definition:string;aggregation_note:string};
 evaluation:{recommendation:'GO'|'CONDITIONAL_GO'|'NO_GO';pass_rate:number|null;risk_score:number|null;gates:Gate[];conditions:string[]};
 explanation:{summary:string;mode:string;remediations:{gate_id:string;action:string}[];note?:string};
 human_decision?:{decision:string;reviewer:string;reason:string;authorized_at:string;scope:string}};
export type Review={review_id:string;release_id:string;reviewer:string;notes:string;risk_level:string;reviewed_at:string};
export const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
async function json<T>(path:string,body?:unknown,token?:string):Promise<T>{const response=await fetch(API+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json',...(token?{[API.startsWith('/')?'X-QA-Reviewer':'Authorization']:'Bearer '+token}:{})},body:JSON.stringify(body)});if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(typeof data?.detail==='string'?data.detail:`Release request failed (${response.status})`);}return response.json();}
export const history=()=>json<Assessment[]>('/releases');
export const reviews=()=>json<Review[]>('/releases/evidence-review');
export const reviewer=()=>json<{reviewer:string;configured:boolean;scope:string}>('/releases/reviewer');
export const policy=()=>json<Record<string,unknown>>('/releases/policy');
export const assess=(release_id:string,execution_ids:string[],review_id:string|null)=>json<Assessment>('/releases',{release_id,execution_ids,review_id,explanation_mode:'demo'});
export const attest=(body:unknown,token:string)=>json<Review>('/releases/evidence-review',body,token);
export const decide=(record:Assessment,decision:string,reviewer:string,reason:string,conditions_acknowledged:boolean,token:string)=>json<Assessment>('/releases/'+encodeURIComponent(record.assessment_id)+'/decision',{decision,reviewer,assessment_hash:record.assessment_hash,reason,conditions_acknowledged},token);
