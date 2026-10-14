export type Analysis = { requirement: string; scenarios: string[]; ambiguities: string[]; status: string; mode: string };
export type AgentAnalysis = { scenarios: string[]; ambiguities: string[]; risks: string[]; summary: string };
export type Workflow = { run_id: string; requirement: string; analysis: AgentAnalysis | null; mode: string | null; status: string; decision?: string; phase?: string; criteria?: Criterion[]; test_cases?: TestCase[]; test_data?: TestData[]; metrics?: Metrics; errors?: {agent: string; message: string}[] };
const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
async function json<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) { const body = await res.json().catch(() => null); throw new Error(body?.detail ? `Request failed (${res.status}): ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)}` : `HTTP ${res.status}`); }
  return res.json();
}
export const analyzeRequirement = (requirement: string) => json<Analysis>('/requirements/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({requirement}) });
export const startWorkflow = (requirement: string) => json<Workflow>('/workflows', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({requirement}) });
export const decideWorkflow = (id: string, decision: 'approve'|'reject') => json<Workflow>(`/workflows/${id}/decision`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({decision}) });

export type Criterion = {id: string; text: string};
export type ExpectedResult = {description: string; needs_review: boolean};
export type TestCase = {id: string; requirement_id: string; scenario_id: string; criterion_ids: string[]; title: string; category: 'positive'|'negative'|'boundary'; priority: string; preconditions: string[]; steps: {action: string}[]; expected_result: ExpectedResult; review_status: 'pending'|'reviewed'};
export type TestData = {id: string; test_case_id: string; kind: 'valid'|'invalid'|'edge'; values: Record<string, unknown>; expected_behavior: string; needs_review: boolean; synthetic: boolean};
export type Metrics = {case_count: number; traceability_percent: number; duplicate_percent: number; criterion_reference_coverage_percent: number; data_link_coverage_percent: number; pending_review_count: number; note: string};
export const getWorkflow = (id: string) => json<Workflow>(`/workflows/${encodeURIComponent(id)}`);
export const editTestCase = (run: string, id: string, edit: Pick<TestCase, 'title'|'expected_result'|'review_status'>) => json<Workflow>(`/workflows/${encodeURIComponent(run)}/test-cases/${encodeURIComponent(id)}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(edit)});
export const editTestData = (run: string, id: string, edit: Pick<TestData, 'values'|'expected_behavior'|'needs_review'>) => json<Workflow>(`/workflows/${encodeURIComponent(run)}/test-data/${encodeURIComponent(id)}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(edit)});
export async function downloadPackage(id: string) {
  const data = await json<Workflow>(`/workflows/${encodeURIComponent(id)}/export`);
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'Agentic_QA_Test_Package.json';
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}


export type EvaluationReport = {dataset:string; mode:string; sample_count:number; passed:number; schema_valid_output_percent:number; scope:string; results:{id:string; schema_valid:boolean; passed:boolean; labeled_title_coverage_percent:number; metrics:Metrics}[]};
export const getEvaluation = () => json<EvaluationReport>('/evaluation/design_benchmark');
