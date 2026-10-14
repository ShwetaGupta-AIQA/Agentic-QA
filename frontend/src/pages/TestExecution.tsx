import {useEffect,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import * as api from '../services/executionApi';

export default function TestExecution(){
 const [params,setParams]=useSearchParams();const id=params.get('execution')||'';
 const [catalog,setCatalog]=useState<api.Suite[]>([]);const [runs,setRuns]=useState<api.Execution[]>([]);
 const [selected,setSelected]=useState<string[]>([]);const [approved,setApproved]=useState(false);
 const [result,setResult]=useState<api.Execution|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 useEffect(()=>{let alive=true;Promise.all([api.suites(),api.history()]).then(([s,r])=>{if(alive){setCatalog(s);setRuns(r);}}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[]);
 useEffect(()=>{if(!id){setResult(null);return;}let alive=true;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{const run=await api.execution(id);if(!alive)return;setResult(run);setError('');if(['queued','running'].includes(run.status))timer=setTimeout(poll,1000);else setRuns(await api.history());}catch(e){if(alive)setError(e instanceof Error?e.message:'Polling failed');}};
  void poll();return()=>{alive=false;clearTimeout(timer);};
 },[id]);
 function toggle(key:string){setSelected(current=>current.includes(key)?current.filter(item=>item!==key):[...current,key]);setApproved(false);}
 async function submit(){setBusy(true);setError('');try{const run=await api.execute(selected);setResult(run);setParams({execution:run.execution_id});setApproved(false);}catch(e){setError(e instanceof Error?e.message:'Execution failed');}finally{setBusy(false);}}
 const running=!!result&&['queued','running'].includes(result.status);
 return <><h1>Test Execution Center</h1><p className="muted">Run reviewed commerce-v1 suites against an isolated local synthetic SUT. Generated test cases are candidates and are not executable code.</p>
 {error&&<p role="alert" className="card error">{error}</p>}
 <section className="card"><h2>Registered suites</h2><p>Local environment only. ECOM IDs are automation registry IDs; generated TC IDs remain separate.</p>
 {catalog.map(item=><label className="check" key={item.id}><input type="checkbox" checked={selected.includes(item.id)} disabled={busy||running} onChange={()=>toggle(item.id)}/>{item.id}: {item.title} ({item.types.join(' + ')} / {item.automation_count} assertions)</label>)}
 <label className="check"><input type="checkbox" checked={approved} disabled={busy||running||!selected.length} onChange={e=>setApproved(e.target.checked)}/>I reviewed these selected registered suites and approve local execution</label>
 <button disabled={!approved||!selected.length||busy||running} onClick={()=>void submit()}>Execute approved tests</button></section>
 {result&&<section className="card" aria-label="Execution results" aria-live="polite"><h2>Execution {result.execution_id}</h2><p role="status">Status: {result.status}</p><div className="quality-grid"><p>Passed: {result.passed}</p><p>Failed: {result.failed}</p><p>Errors: {result.errors}</p><p>Skipped: {result.skipped}</p><p>Duration: {result.duration_seconds}s</p></div><p>{result.message}</p>
 {result.results.map((row,i)=><article className="card" key={i}><strong>{row.test_id} / {row.name} / {row.type}: {row.status}</strong><p>{row.classification}</p>{row.message&&<pre>{row.message}</pre>}</article>)}
 {['failed','error','timeout'].includes(result.status)&&<p><Link to={'/defects?execution='+encodeURIComponent(result.execution_id)}>Analyze failure evidence</Link></p>}<h3>Evidence</h3>{result.artifacts.length?result.artifacts.map(path=><p key={path}><a href={api.artifactUrl(result.execution_id,path)} target="_blank" rel="noreferrer">{path}</a></p>):<p>Evidence appears when execution finishes.</p>}</section>}
 <section className="card"><h2>Recent executions</h2>{runs.length?runs.map(run=><p key={run.execution_id}><button onClick={()=>setParams({execution:run.execution_id})}>{run.execution_id} / {run.status} / {run.passed} passed</button></p>):<p>No real executions recorded yet.</p>}</section>
 </>;
}
