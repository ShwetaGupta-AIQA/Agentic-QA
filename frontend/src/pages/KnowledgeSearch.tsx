import {useEffect,useState} from 'react';
import * as api from '../services/intelligenceApi';
import SourceList from '../components/SourceList';
export default function KnowledgeSearch(){
 const [query,setQuery]=useState('coupon expiry midnight UTC');const [kind,setKind]=useState('');const [version,setVersion]=useState('');
 const [result,setResult]=useState<api.SearchResult|null>(null);const [status,setStatus]=useState<{indexed_chunks:number;embedding_mode:string;embedding_model:string}|null>(null);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [sourceId,setSourceId]=useState('');const [sourceType,setSourceType]=useState('execution');
 const [evaluation,setEvaluation]=useState<Awaited<ReturnType<typeof api.evaluation>>|null>(null);
 useEffect(()=>{let active=true;api.status().then(value=>{if(active)setStatus(value);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
 async function task(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'Request failed');}finally{setBusy(false);}}
 return <><h1>Knowledge Search</h1><p className="muted">Search versioned requirements, tests, historical defects and execution evidence. Retrieved history is context, not proof.</p>
 {status&&<p>{status.indexed_chunks} indexed chunks / {status.embedding_mode} embeddings / {status.embedding_model}</p>}{error&&<p role="alert" className="card error">{error}</p>}
 <section className="card"><h2>Ingest knowledge</h2><button disabled={busy} onClick={()=>void task(async()=>{await api.ingest();setStatus(await api.status());})}>Ingest synthetic demo corpus</button>
 <label>Record type<select value={sourceType} onChange={e=>setSourceType(e.target.value)}><option value="execution">Completed execution</option><option value="workflow">Approved complete workflow</option></select></label><label>Record ID<input value={sourceId} onChange={e=>setSourceId(e.target.value)}/></label><button disabled={busy||!sourceId.trim()} onClick={()=>void task(async()=>{if(sourceType==='execution')await api.ingestExecution(sourceId.trim());else await api.ingestWorkflow(sourceId.trim());setStatus(await api.status());})}>Ingest selected record</button></section>
 <form className="card" onSubmit={e=>{e.preventDefault();void task(async()=>{setResult(await api.search(query,kind,version));});}}><label>Knowledge query<input required minLength={3} maxLength={2000} value={query} onChange={e=>{setQuery(e.target.value);setResult(null);}}/></label><label>Document type<select value={kind} onChange={e=>setKind(e.target.value)}><option value="">All types</option>{['requirement','test','defect','execution','log'].map(value=><option key={value}>{value}</option>)}</select></label><label>Source version<input placeholder="Any version" value={version} onChange={e=>setVersion(e.target.value)}/></label><button disabled={busy||query.trim().length<3}>Search knowledge</button></form>
 {result&&<><p>{result.note}</p><SourceList sources={result.sources}/></>}
 <section className="card"><h2>Measured retrieval evaluation</h2><button disabled={busy} onClick={()=>void task(async()=>setEvaluation(await api.evaluation()))}>Load Recall@5 evaluation</button>{evaluation&&<><p>{evaluation.queries} labeled queries / Recall@5 {(100*evaluation.mean_recall_at_5).toFixed(1)}% / Precision@5 {(100*evaluation.mean_precision_at_5).toFixed(1)}%</p><p>Source references: {evaluation.source_reference_percent}%</p><p>{evaluation.scope}</p></>}</section>
 </>;
}
