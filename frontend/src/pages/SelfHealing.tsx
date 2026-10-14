import {useEffect,useState} from 'react';
import * as api from '../services/healingApi';
export default function SelfHealing(){
 const [records,setRecords]=useState<api.Proposal[]>([]);const [record,setRecord]=useState<api.Proposal|null>(null);const [candidate,setCandidate]=useState('role_coupon');
 const [reviewer,setReviewer]=useState('');const [approved,setApproved]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [mcp,setMcp]=useState<api.MCPInfo|null>(null);const [tool,setTool]=useState('get_execution');const [argumentsText,setArgumentsText]=useState('{}');const [toolResult,setToolResult]=useState<unknown>();
 useEffect(()=>{let active=true;api.history().then(value=>{if(active)setRecords(value);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
 async function task(fn:()=>Promise<void>){setBusy(true);setError('');setApproved(false);try{await fn();}catch(e){setError(e instanceof Error?e.message:'Operation failed');}finally{setBusy(false);}}
 function choose(value:api.Proposal){setRecord(value);setCandidate(value.selected_candidate||value.candidates[0]?.id||'role_coupon');setApproved(false);}
 const available=record&&['proposed','validated'].includes(record.status);
 const canApprove=!!record&&record.status==='validated'&&record.validation?.passed&&record.selected_candidate===candidate&&approved&&reviewer.trim().length>=2&&!busy;
 return <><h1>Self-Healing Center</h1><p className="muted">Locator-only proposals for the registered local coupon example. Assertion and infrastructure failures are not automatically healed.</p>
 {error&&<p role="alert" className="card error">{error}</p>}
 <section className="card"><h2>Known broken-locator demonstration</h2><p>Reproduce the missing #apply-coupon locator, capture DOM/trace, and propose unique coupon-button alternatives. Starting or validating never edits the source.</p><button disabled={busy} onClick={()=>void task(async()=>{choose(await api.demonstrate());setRecords(await api.history());})}>Reproduce and propose repair</button></section>
 {record&&<section className="card" aria-label="Repair proposal"><h2>Proposal {record.proposal_id}</h2><p>Status: {record.status}</p><p>Baseline: {record.baseline.category} / {record.baseline.passed?'passed':'failed'}</p><p>{record.note}</p><h3>Original locator</h3><pre>{JSON.stringify(record.original_locator,null,2)}</pre>
 <label>Candidate locator<select disabled={busy||!available} value={candidate} onChange={e=>{setCandidate(e.target.value);setApproved(false);}}>{record.candidates.map(item=><option key={item.id} value={item.id}>{item.id}: {JSON.stringify(item.locator)}</option>)}</select></label>
 {record.candidates.map(item=><p key={item.id}>{item.id}: {item.matches} captured DOM match / {item.reason}</p>)}
 <button disabled={busy||!available||!record.candidates.length} onClick={()=>void task(async()=>choose(await api.validate(record.proposal_id,candidate)))}>Validate full coupon test</button>
 {record.validation&&<p>Candidate validation: {record.validation.passed?'Passed':'Failed'} / {record.validation.category} / {record.validation.matches??'unknown'} matches</p>}
 {record.patch_preview&&<><h3>Proposed locator-only patch</h3><pre>{record.patch_preview}</pre></>}
 <h3>Human decision</h3><label>Reviewer name<input disabled={busy} value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label className="check"><input type="checkbox" disabled={busy||record.status!=='validated'||record.selected_candidate!==candidate} checked={approved} onChange={e=>setApproved(e.target.checked)}/>I reviewed the patch and passing full-test evidence and approve this locator-only change</label>
 <button disabled={!canApprove} onClick={()=>void task(async()=>{choose(await api.decision(record.proposal_id,'approve',reviewer,record.validation!.validation_id,true));setRecords(await api.history());})}>Approve and apply locator patch</button>
 <button disabled={busy||!available||reviewer.trim().length<2} onClick={()=>void task(async()=>{choose(await api.decision(record.proposal_id,'reject',reviewer,record.validation?.validation_id||'',false));setRecords(await api.history());})}>Reject proposal</button>
 {record.audit&&<><h3>Patch audit</h3><pre>{JSON.stringify(record.audit,null,2)}</pre></>}{record.regression&&<p>Post-application full-test regression: {record.regression.passed?'Passed':'Failed — investigate; no assertions were changed'}</p>}
 <h3>Evidence</h3>{['dom.json','dom.html','failure.png','trace.zip'].map(name=><p key={name}><a href={api.evidence(record.proposal_id,record.baseline.validation_id,'evidence/test_coupon_locator/'+name)} target="_blank" rel="noreferrer">Baseline {name}</a></p>)}
 {record.validation&&<p><a href={api.evidence(record.proposal_id,record.validation.validation_id,'junit.xml')}>Candidate JUnit</a> / <a href={api.evidence(record.proposal_id,record.validation.validation_id,'evidence/test_coupon_locator/trace.zip')}>Candidate trace</a></p>}
 </section>}
 <section className="card"><h2>Saved proposals</h2>{records.map(item=><p key={item.proposal_id}><button disabled={busy} onClick={()=>choose(item)}>{item.proposal_id} / {item.status}</button></p>)}</section>
 <section className="card"><h2>Local MCP tools</h2><button disabled={busy} onClick={()=>void task(async()=>setMcp(await api.mcpTools()))}>Connect and inspect MCP tools</button>
 {mcp&&<><p>{mcp.transport} / {mcp.authentication} / Patch tools: {mcp.patch_tools?'present':'none'}</p>{mcp.tools.map(item=><details key={item.name}><summary>{item.name} / {item.scope}</summary><p>{item.description}</p><pre>{JSON.stringify(item.input_schema,null,2)}</pre></details>)}
 <label>Read-only MCP tool<select value={tool} onChange={e=>setTool(e.target.value)}>{mcp.tools.map(item=><option key={item.name}>{item.name}</option>)}</select></label>
 <label>Tool arguments JSON<textarea value={argumentsText} onChange={e=>setArgumentsText(e.target.value)}/></label><button disabled={busy} onClick={()=>void task(async()=>{const args=JSON.parse(argumentsText);if(!args||typeof args!=='object'||Array.isArray(args))throw new Error('Arguments must be a JSON object');setToolResult(await api.mcpCall(tool,args));})}>Read through MCP</button>{toolResult!==undefined&&<pre>{JSON.stringify(toolResult,null,2)}</pre>}</>}
 </section></>;
}
