import { useState } from 'react';
import { getEvaluation, type EvaluationReport } from './api';

export default function Evaluation() {
 const [report,setReport]=useState<EvaluationReport|null>(null);
 const [error,setError]=useState('');const [loading,setLoading]=useState(false);
 return <section className="card"><h2>Synthetic Benchmark</h2><p className="muted">Measured demo outputs, separate from illustrative execution KPIs.</p>
 <button disabled={loading} onClick={async()=>{setLoading(true);setError('');try{setReport(await getEvaluation());}catch(err){setError(err instanceof Error?err.message:'Evaluation unavailable');}finally{setLoading(false);}}}>{loading?'Loading evaluation...':'Load measured evaluation'}</button>
 {error&&<p role="alert">{error}</p>}{report&&<><p>{report.passed}/{report.sample_count} labeled examples passed / Schema-valid output: {report.schema_valid_output_percent}%</p><p>{report.scope}</p>{report.results.map(sample=><div key={sample.id} className="line"><span>{sample.id}</span><span>Traceability {sample.metrics.traceability_percent}% / Duplicates {sample.metrics.duplicate_percent}% / Title-label coverage {sample.labeled_title_coverage_percent}%</span></div>)}</>}
 </section>;
}
