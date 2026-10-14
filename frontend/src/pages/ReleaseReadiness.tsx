import {useEffect,useState} from 'react';
import * as api from '../services/releaseApi';
export default function ReleaseReadiness(){
 const [release,setRelease]=useState('commerce-1.0.0');const [executions,setExecutions]=useState('');const [reviewId,setReviewId]=useState('');
 const [record,setRecord]=useState<api.Assessment|null>(null);const [history,setHistory]=useState<api.Assessment[]>([]);const [reviews,setReviews]=useState<api.Review[]>([]);
 const [reviewer,setReviewer]=useState('local-reviewer');const [token,setToken]=useState('');const [reason,setReason]=useState('');const [ack,setAck]=useState(false);
 const [defects,setDefects]=useState('[]');const [drafts,setDrafts]=useState('');const [risk,setRisk]=useState('low');const [unresolved,setUnresolved]=useState(0);const [notes,setNotes]=useState('');const [reviewed,setReviewed]=useState(false);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [policy,setPolicy]=useState<Record<string,unknown>|null>(null);
 useEffect(()=>{let active=true;Promise.all([api.history(),api.reviews(),api.reviewer(),api.policy()]).then(([items,rs,auth,p])=>{if(active){setHistory(items);setReviews(rs);setReviewer(auth.reviewer);setPolicy(p);}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
 async function task(fn:()=>Promise<void>){setBusy(true);setError('');setAck(false);try{await fn();}catch(e){setError(e instanceof Error?e.message:'Release action failed');}finally{setBusy(false);}}
 const eligible=!!record&&record.status==='awaiting_review'&&record.approval_available!==false;
 const canAuthorize=eligible&&record.evaluation.recommendation!=='NO_GO'&&token.length>=32&&reason.trim().length>=10&&!busy&&(record.evaluation.recommendation!=='CONDITIONAL_GO'||ack);
 return <><h1>Release Readiness</h1><p className="muted">Deterministic quality gates produce a recommendation. Human authorization is separate and records no deployment.</p>{error&&<p role="alert" className="card error">{error}</p>}
 <form className="card" onSubmit={e=>{e.preventDefault();void task(async()=>{setRecord(await api.assess(release,executions.split(',').map(value=>value.trim()).filter(Boolean),reviewId||null));setHistory(await api.history());});}}><label>Release ID<input required value={release} onChange={e=>{setRelease(e.target.value);setReviewed(false);setReviewId('');setRecord(null);setAck(false);}}/></label><label>Execution IDs (comma separated)<textarea value={executions} onChange={e=>setExecutions(e.target.value)}/></label><label>Authorized defect/risk review<select value={reviewId} onChange={e=>setReviewId(e.target.value)}><option value="">Missing review — remains unknown</option>{reviews.filter(item=>item.release_id===release).map(item=><option key={item.review_id} value={item.review_id}>{item.review_id}: {item.risk_level} / {item.reviewer}</option>)}</select></label><button disabled={busy||!release.trim()}>Evaluate release gates</button></form>
 <details className="card"><summary>Policy thresholds</summary><pre>{JSON.stringify(policy,null,2)}</pre></details>
 <details className="card"><summary>Authorized defect and regression-risk evidence review</summary><p>Defect drafts are not confirmed defects. An empty register is an explicit reviewer attestation, not an inference from missing files.</p>
 <label>Configured reviewer<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>Release reviewer credential<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><p className="muted">Use the local QA_RELEASE_REVIEW_TOKEN from backend/.env. The credential is not saved in browser storage.</p>
 <label>Confirmed defects JSON<textarea rows={5} value={defects} onChange={e=>{setDefects(e.target.value);setReviewed(false);}}/></label>
 <p>Example entry: id, severity (critical/high/medium/low), status (open/resolved), optional source_draft_id.</p>
 <label>Reviewed draft IDs (comma separated)<input value={drafts} onChange={e=>{setDrafts(e.target.value);setReviewed(false);}}/></label>
 <label>Regression risk<select value={risk} onChange={e=>{setRisk(e.target.value);setReviewed(false);}}><option>low</option><option>medium</option><option>high</option></select></label>
 <label>Unresolved regression risks<input type="number" min={0} max={100} value={unresolved} onChange={e=>{setUnresolved(Number(e.target.value));setReviewed(false);}}/></label>
 <label>Evidence review notes<textarea value={notes} onChange={e=>{setNotes(e.target.value);setReviewed(false);}}/></label>
 <label className="check"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I reviewed confirmed defects and regression risks for this release</label>
 <button disabled={busy||!reviewed||token.length<32||notes.trim().length<10} onClick={()=>void task(async()=>{const register:unknown=JSON.parse(defects);if(!Array.isArray(register))throw new Error('Defect register must be a JSON array');const value=await api.attest({release_id:release,reviewer,defects:register,risk_level:risk,unresolved_regression_risks:unresolved,notes,reviewed,reviewed_draft_ids:drafts.split(',').map(value=>value.trim()).filter(Boolean)},token);setReviews(await api.reviews());setReviewId(value.review_id);})}>Record authorized evidence review</button>
 </details>
 {record&&<section className="card" aria-label="Release assessment"><h2>{record.release_id}: {record.evaluation.recommendation.replace(/_/g,' ')}</h2><p>Status: {record.status} / Snapshot: {record.assessment_hash}</p>
 <div className="quality-grid"><p>Pass rate: {record.evaluation.pass_rate===null?'Unknown':record.evaluation.pass_rate+'%'}</p><p>Requirement execution coverage: {record.aggregate.evidence.requirement_coverage===null?'Unknown':record.aggregate.evidence.requirement_coverage+'%'}</p><p>Open critical defects: {record.aggregate.evidence.critical_defects_open??'Unknown'}</p><p>Open high defects: {record.aggregate.evidence.high_defects_open??'Unknown'}</p><p>Risk index: {record.evaluation.risk_score??'Unknown'}</p></div>
 <p>{record.aggregate.coverage_definition}</p><p>{record.aggregate.aggregation_note}</p>
 <h3>Explicit gate results</h3>{record.evaluation.gates.map(gate=><article className="card" key={gate.id}><strong>{gate.id}: {gate.status} / {gate.blocking?'Blocking':'Advisory'}</strong><p>Observed: {gate.observed===null?'Missing evidence':JSON.stringify(gate.observed)} / Policy: {gate.policy}</p>{gate.status!=='PASS'&&<p>{gate.remediation}</p>}<details><summary>Gate source references</summary><p>{gate.source_ids.join(', ')}</p></details></article>)}
 <h3>Explanation ({record.explanation.mode})</h3><p>{record.explanation.summary}</p>{record.explanation.note&&<p>{record.explanation.note}</p>}
 <h3>Source evidence</h3>{record.aggregate.sources.map(source=><p key={source.id}>{source.id} / {source.kind} / SHA256 {source.sha256}</p>)}
 <a href={api.API+'/releases/'+encodeURIComponent(record.assessment_id)+'/export'}>Export release report JSON</a>
 <h3>Final human decision</h3><p>Configured reviewer: {reviewer}. Enter the credential in the evidence-review panel above.</p><label>Decision rationale<textarea value={reason} onChange={e=>setReason(e.target.value)}/></label>
 <label className="check"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>I acknowledge the listed release conditions</label>
 {record.evaluation.conditions.map(text=><p key={text}>{text}</p>)}
 <button disabled={!canAuthorize} onClick={()=>void task(async()=>{setRecord(await api.decide(record,record.evaluation.recommendation,reviewer,reason,ack,token));setHistory(await api.history());})}>Authorize recommended release decision</button>
 <button disabled={!eligible||!token||reason.trim().length<10||busy} onClick={()=>void task(async()=>{setRecord(await api.decide(record,'NO_GO',reviewer,reason,false,token));setHistory(await api.history());})}>Record human NO-GO</button>
 {!eligible&&record.status==='awaiting_review'&&<p>Backend checkpoint expired; create a fresh assessment before authorization.</p>}
 {record.human_decision&&<pre>{JSON.stringify(record.human_decision,null,2)}</pre>}
 </section>}
 <section className="card"><h2>Saved release assessments</h2>{history.map(item=><p key={item.assessment_id}><button disabled={busy} onClick={()=>{setRecord(item);setAck(false);}}>{item.release_id}: {item.evaluation.recommendation} / {item.status}</button></p>)}</section>
 </>;
}
