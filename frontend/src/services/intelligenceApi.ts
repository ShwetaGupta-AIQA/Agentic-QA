export type Source={source_id:string;citation_id:string;chunk_id:string;title:string;text:string;score:number|null;metadata:{project:string;kind:string;source_version:string;synthetic:boolean;test_id:string;requirement_id:string}};
export type SearchResult={query:string;sources:Source[];embedding_mode:string;note:string};
export type Impact={change:string;impacted_tests:{test_id:string;title:string;priority:string;reason:string;citation_ids:string[];registered_automation:boolean;needs_review:boolean}[];sources:Source[];embedding_mode:string;note:string};
export type DefectReport={report_id:string;execution_id:string;mode:string;note:string;findings:{test_id:string;title:string;classification:string;observed:{name:string;message:string;status:string};hypotheses:{text:string;confidence:string;citation_ids:string[]}[];next_steps:string[];sources:Source[];review_status:string;human_review_required:boolean}[]};
export const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
async function json<T>(path:string,body?:unknown):Promise<T>{const response=await fetch(API+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(typeof data?.detail==='string'?data.detail:`Intelligence request failed (${response.status})`);}return response.json();}
export const status=()=>json<{indexed_chunks:number;embedding_mode:string;embedding_model:string}>('/knowledge/status');
export const ingest=()=>json<{documents:number;indexed_chunks:number}>('/knowledge/ingest/demo',{});
export const search=(query:string,kind:string,version:string)=>json<SearchResult>('/knowledge/search',{query,project:'commerce',kind:kind||null,source_version:version||null,top_k:5});
export const impact=(query:string)=>json<Impact>('/intelligence/impact',{query,project:'commerce',top_k:10});
export const analyze=(execution_id:string)=>json<DefectReport>('/intelligence/defects',{execution_id,mode:'demo'});
export const drafts=()=>json<DefectReport[]>('/intelligence/defects');
export const ingestExecution=(id:string)=>json('/knowledge/ingest/executions/'+encodeURIComponent(id),{});
export const ingestWorkflow=(id:string)=>json('/knowledge/ingest/workflows/'+encodeURIComponent(id),{});
export const evaluation=()=>json<{queries:number;mean_recall_at_5:number;mean_precision_at_5:number;source_reference_percent:number;scope:string}>('/evaluation/retrieval');
