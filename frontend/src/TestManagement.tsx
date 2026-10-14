import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { downloadPackage, editTestCase, editTestData, getWorkflow, type TestCase, type TestData, type Workflow } from './api';

function CaseEditor({item, busy, save}: {item: TestCase; busy: boolean; save: (edit: Pick<TestCase,'title'|'expected_result'|'review_status'>) => void}) {
  const [title, setTitle] = useState(item.title);
  const [expected, setExpected] = useState(item.expected_result.description);
  const [confirmed, setConfirmed] = useState(!item.expected_result.needs_review);
  return <form className="editor" onSubmit={event => {event.preventDefault(); save({title, expected_result:{description:expected, needs_review:!confirmed}, review_status:confirmed?'reviewed':'pending'});}}>
    <label>Case title<input required value={title} onChange={e=>setTitle(e.target.value)}/></label>
    <label>Expected result<textarea required value={expected} onChange={e=>setExpected(e.target.value)}/></label>
    <label className="check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I confirmed this expected result against acceptance criteria</label>
    <button disabled={busy || !title.trim() || !expected.trim()}>Save test case</button>
  </form>;
}

function DataEditor({item, busy, save}: {item: TestData; busy: boolean; save:(edit:Pick<TestData,'values'|'expected_behavior'|'needs_review'>)=>void}) {
  const [values, setValues] = useState(JSON.stringify(item.values,null,2));
  const [expected, setExpected] = useState(item.expected_behavior);
  const [confirmed, setConfirmed] = useState(!item.needs_review);
  const [error, setError] = useState('');
  return <form className="editor" onSubmit={e=>{e.preventDefault();try {const parsed:unknown=JSON.parse(values);if(!parsed || typeof parsed!=='object' || Array.isArray(parsed))throw new Error('Fixture must be a JSON object');setError('');save({values:parsed as Record<string,unknown>, expected_behavior:expected, needs_review:!confirmed});}catch(err){setError(err instanceof Error?err.message:'Invalid JSON');}}}>
    <label>Synthetic fixture JSON<textarea rows={8} required value={values} onChange={e=>setValues(e.target.value)}/></label>
    <label>Expected data behavior<textarea required value={expected} onChange={e=>setExpected(e.target.value)}/></label>
    <label className="check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I reviewed the synthetic values and assumptions</label>
    {error && <p role="alert">{error}</p>}<button disabled={busy || !expected.trim()}>Save test data</button>
  </form>;
}

export default function TestManagement({dataMode=false}:{dataMode?:boolean}) {
  const [params, setParams] = useSearchParams();
  const runId = params.get('run') || '';
  const [input, setInput] = useState(runId);
  const [run, setRun] = useState<Workflow|null>(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [review, setReview] = useState('all');
  const [editId, setEditId] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(()=>{
    let active=true;setRun(null);setError('');setEditId('');setInput(runId);
    if(!runId){setBusy(false);return;}
    setBusy(true);
    getWorkflow(runId).then(value=>{if(active)setRun(value);}).catch(err=>{if(active)setError(err.message);}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[runId]);
  useEffect(()=>{setCategory('all');setSearch('');setReview('all');setEditId('');},[dataMode]);
  async function saveCase(item: TestCase, edit: Pick<TestCase,'title'|'expected_result'|'review_status'>) {
    setBusy(true);setError('');try {setRun(await editTestCase(runId,item.id,edit));setEditId('');}catch(err){setError(err instanceof Error?err.message:'Save failed');}finally{setBusy(false);}
  }
  async function saveData(item: TestData, edit:Pick<TestData,'values'|'expected_behavior'|'needs_review'>) {
    setBusy(true);setError('');try {setRun(await editTestData(runId,item.id,edit));setEditId('');}catch(err){setError(err instanceof Error?err.message:'Save failed');}finally{setBusy(false);}
  }
  const ready = run?.phase==='ready_for_review';
  const cases=(run?.test_cases||[]).filter(item=>(item.id+' '+item.title).toLowerCase().includes(search.toLowerCase()) && (category==='all'||item.category===category) && (review==='all'||(review==='review'?(item.review_status==='pending'||item.expected_result.needs_review):(item.review_status==='reviewed'&&!item.expected_result.needs_review))));
  const datasets=(run?.test_data||[]).filter(item=>(item.id+' '+item.test_case_id+' '+JSON.stringify(item.values)).toLowerCase().includes(search.toLowerCase()) && (category==='all'||item.kind===category) && (review==='all'||(review==='review'?item.needs_review:!item.needs_review)));
  return <>
    <h1>{dataMode?'Test Data Explorer':'Test Case Management'}</h1>
    <p className="muted">Synthetic candidates and reviewed expectations. Generation does not execute tests.</p>
    <form className="card inline-form" onSubmit={e=>{e.preventDefault();setParams({run:input.trim()});}}><label htmlFor="run-id">Workflow ID</label><input id="run-id" required value={input} onChange={e=>setInput(e.target.value)}/><button disabled={busy}>Load workflow</button></form>
    {busy&&<p role="status">Loading...</p>}{error&&<p className="card error" role="alert">{error}</p>}
    {!runId&&<p><Link to="/requirements">Submit and approve a requirement</Link> to generate a test package.</p>}
    {run&&<>
      <div className="card"><strong>Workflow: {run.status} / {run.phase}</strong><p>{run.requirement}</p><p className="muted">Mode: {run.mode}</p>{run.errors?.map(item=><p key={item.agent} className="error-text">{item.agent}: {item.message}</p>)}
        {!ready&&<p>No complete package is available. Review the requirements or recorded failure.</p>}
        <div className="approval-actions"><Link to={'/test-cases?run='+encodeURIComponent(runId)}>Test cases</Link><Link to={'/test-data?run='+encodeURIComponent(runId)}>Test data</Link>
        <button disabled={!ready||busy} onClick={async()=>{setError('');try{await downloadPackage(runId);}catch(err){setError(err instanceof Error?err.message:'Export failed');}}}>Export JSON package</button></div>
      </div>
      {run.metrics&&<section className="card" aria-label="Quality metrics"><h2>Measured package metrics</h2><dl className="quality-grid"><div><dt>Traceability</dt><dd>{run.metrics.traceability_percent}%</dd></div><div><dt>Exact duplicates</dt><dd>{run.metrics.duplicate_percent}%</dd></div><div><dt>Clause references</dt><dd>{run.metrics.criterion_reference_coverage_percent}%</dd></div><div><dt>Cases with data</dt><dd>{run.metrics.data_link_coverage_percent}%</dd></div><div><dt>Pending case review</dt><dd>{run.metrics.pending_review_count}</dd></div></dl><p className="muted">{run.metrics.note}</p></section>}
      {!!run.criteria?.length&&<details className="card"><summary>Requirement traceability clauses</summary>{run.criteria.map(c=><p key={c.id}><strong>{c.id}</strong> {c.text}</p>)}</details>}
      {ready&&<>{dataMode&&<section className="card"><h2>Synthetic data overview</h2><p>{run.test_data?.length||0} datasets / {run.test_data?.filter(item=>!item.needs_review).length||0} reviewed / {run.test_data?.filter(item=>item.needs_review).length||0} need review</p></section>}<div className="card filters"><label>Search {dataMode?'data':'test cases'}<input value={search} onChange={e=>setSearch(e.target.value)}/></label><label>Category<select value={category} onChange={e=>setCategory(e.target.value)}><option value="all">All</option>{(dataMode?['valid','invalid','edge']:['positive','negative','boundary']).map(value=><option key={value}>{value}</option>)}</select></label><label>Review status<select value={review} onChange={e=>setReview(e.target.value)}><option value="all">All</option><option value="review">Needs review</option><option value="reviewed">Reviewed</option></select></label></div>
      <p>{dataMode?datasets.length:cases.length} matching {dataMode?'datasets':'cases'}</p>
      {dataMode?datasets.map(item=><article className="card" key={item.id}><h2>{item.id} / {item.test_case_id}</h2><p>{item.kind} / {item.needs_review?'Needs review':'Reviewed'} / Synthetic</p><pre>{JSON.stringify(item.values,null,2)}</pre><p>{item.expected_behavior}</p><button disabled={busy} onClick={()=>setEditId(editId===item.id?'':item.id)}>Edit {item.id}</button>{editId===item.id&&<DataEditor key={item.id} item={item} busy={busy} save={edit=>void saveData(item,edit)}/>}</article>):cases.map(item=><article className="card" key={item.id}><h2>{item.id}: {item.title}</h2><p>{item.category} / {item.priority} / {item.review_status}{item.expected_result.needs_review?' / Expected result needs review':''}</p><p>Trace: {item.requirement_id} / {item.scenario_id} / {item.criterion_ids.join(', ')}</p><h3>Preconditions</h3><ul>{item.preconditions.map(text=><li key={text}>{text}</li>)}</ul><h3>Steps</h3><ol>{item.steps.map((step,i)=><li key={i}>{step.action}</li>)}</ol><h3>Expected result</h3><p>{item.expected_result.description}</p><button disabled={busy} onClick={()=>setEditId(editId===item.id?'':item.id)}>Edit {item.id}</button>{editId===item.id&&<CaseEditor key={item.id} item={item} busy={busy} save={edit=>void saveCase(item,edit)}/>}</article>)}
      </>}
    </>}
  </>;
}
