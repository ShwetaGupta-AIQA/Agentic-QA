import { afterEach, expect, test, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

const caseOne={id:'TC-001',requirement_id:'REQ-001',scenario_id:'SC-001',criterion_ids:['AC-001'],title:'Valid coupon',category:'positive',priority:'high',preconditions:['Synthetic cart'],steps:[{action:'Apply coupon'}],expected_result:{description:'Discount matches rule',needs_review:true},review_status:'pending'};
const caseTwo={...caseOne,id:'TC-002',title:'Invalid coupon',category:'negative'};
const data={id:'TD-001',test_case_id:'TC-001',kind:'valid',values:{coupon:'SAVE10',cart_total:'1000'},expected_behavior:'Discount matches rule',needs_review:true,synthetic:true};
const run={run_id:'r-1',requirement:'Apply coupon during checkout',status:'approved',mode:'demo',phase:'ready_for_review',analysis:{scenarios:[],ambiguities:[],risks:[],summary:'Demo'},test_cases:[caseOne,caseTwo],test_data:[data],criteria:[{id:'AC-001',text:'Coupon acceptance'}],metrics:{traceability_percent:100,duplicate_percent:0,criterion_reference_coverage_percent:100,data_link_coverage_percent:50,pending_review_count:2,note:'References are not semantic coverage'}};
const response=(body:unknown)=>({ok:true,status:200,json:async()=>body});
const mount=(path='/test-cases?run=r-1')=>render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
afterEach(()=>vi.unstubAllGlobals());

test('loads cases with traceability and metrics',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(run)));mount();
 expect(await screen.findByText('TC-001: Valid coupon')).toBeInTheDocument();
 expect(screen.getAllByText('Trace: REQ-001 / SC-001 / AC-001')).toHaveLength(2);
 expect(screen.getByText('References are not semantic coverage')).toBeInTheDocument();
});
test('filters by category and search',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(run)));mount();await screen.findByText('TC-001: Valid coupon');
 fireEvent.change(screen.getByLabelText('Category'),{target:{value:'negative'}});
 expect(screen.queryByText('TC-001: Valid coupon')).not.toBeInTheDocument();
 expect(screen.getByText('TC-002: Invalid coupon')).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Search test cases'),{target:{value:'nothing'}});
 expect(screen.getByText('0 matching cases')).toBeInTheDocument();
});
test('saves explicit case review',async()=>{
 const fetchMock=vi.fn().mockResolvedValueOnce(response(run)).mockResolvedValueOnce(response({...run,test_cases:[{...caseOne,title:'Reviewed coupon',review_status:'reviewed',expected_result:{description:'Confirmed discount',needs_review:false}}]}));
 vi.stubGlobal('fetch',fetchMock);mount();await screen.findByText('TC-001: Valid coupon');
 fireEvent.click(screen.getByRole('button',{name:'Edit TC-001'}));
 fireEvent.change(screen.getByLabelText('Case title'),{target:{value:'Reviewed coupon'}});
 fireEvent.change(screen.getByLabelText('Expected result'),{target:{value:'Confirmed discount'}});
 fireEvent.click(screen.getByLabelText('I confirmed this expected result against acceptance criteria'));
 fireEvent.click(screen.getByRole('button',{name:'Save test case'}));
 expect(await screen.findByText('TC-001: Reviewed coupon')).toBeInTheDocument();
 expect(JSON.parse(fetchMock.mock.calls[1][1].body).review_status).toBe('reviewed');
});
test('explores linked synthetic fixtures',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(run)));mount('/test-data?run=r-1');
 expect(await screen.findByText('TD-001 / TC-001')).toBeInTheDocument();
 expect(screen.getByText('valid / Needs review / Synthetic')).toBeInTheDocument();
});
test('invalid fixture JSON cannot be saved',async()=>{
 const fetchMock=vi.fn().mockResolvedValue(response(run));vi.stubGlobal('fetch',fetchMock);mount('/test-data?run=r-1');
 fireEvent.click(await screen.findByRole('button',{name:'Edit TD-001'}));
 fireEvent.change(screen.getByLabelText('Synthetic fixture JSON'),{target:{value:'not json'}});
 fireEvent.click(screen.getByRole('button',{name:'Save test data'}));
 expect(await screen.findByRole('alert')).toBeInTheDocument();expect(fetchMock).toHaveBeenCalledTimes(1);
});
test('failed agent prevents package export',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...run,phase:'failed',errors:[{agent:'test_data',message:'Test data failed'}]})));mount();
 expect(await screen.findByText('test_data: Test data failed')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Export JSON package'})).toBeDisabled();
});
test('empty workspace explains how to start',()=>{
 mount('/test-cases');expect(screen.getByText('Submit and approve a requirement')).toBeInTheDocument();
});


test('dashboard loads measured demo evaluation',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({dataset:'design_benchmark-demo-v1',mode:'demo',sample_count:3,passed:3,schema_valid_output_percent:100,scope:'Demo examples only',results:[]})));
 mount('/');fireEvent.click(screen.getByRole('button',{name:'Load measured evaluation'}));
 expect(await screen.findByText('3/3 labeled examples passed / Schema-valid output: 100%')).toBeInTheDocument();
 expect(screen.getByText('Demo examples only')).toBeInTheDocument();
});
