import {afterEach,expect,test,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import KnowledgeSearch from './KnowledgeSearch';
import RegressionImpact from './RegressionImpact';
import DefectIntelligence from './DefectIntelligence';
import * as api from '../services/intelligenceApi';
vi.mock('../services/intelligenceApi',()=>({API:'',status:vi.fn(),ingest:vi.fn(),search:vi.fn(),impact:vi.fn(),analyze:vi.fn(),drafts:vi.fn(),evaluation:vi.fn(),ingestExecution:vi.fn(),ingestWorkflow:vi.fn()}));
const source={source_id:'REQ-005',citation_id:'REQ-005@commerce-v1#0',chunk_id:'hash',title:'Expiry rule',text:'Reject at midnight UTC',score:.9,metadata:{project:'commerce',kind:'requirement',source_version:'commerce-v1',synthetic:true,test_id:'ECOM-005',requirement_id:'REQ-005'}};
afterEach(()=>vi.clearAllMocks());
function mount(node:React.ReactNode){return render(<MemoryRouter>{node}</MemoryRouter>);}
test('knowledge search shows traceable source and version filters',async()=>{
 vi.mocked(api.status).mockResolvedValue({indexed_chunks:30,embedding_mode:'demo',embedding_model:'hash'});
 vi.mocked(api.search).mockResolvedValue({query:'coupon',sources:[source],embedding_mode:'demo',note:'Lexical baseline'});
 mount(<KnowledgeSearch/>);
 fireEvent.change(screen.getByLabelText('Document type'),{target:{value:'requirement'}});
 fireEvent.change(screen.getByLabelText('Source version'),{target:{value:'commerce-v1'}});
 fireEvent.click(screen.getByRole('button',{name:'Search knowledge'}));
 expect(await screen.findByText('REQ-005: Expiry rule')).toBeInTheDocument();
 expect(api.search).toHaveBeenCalledWith('coupon expiry midnight UTC','requirement','commerce-v1');
 expect(screen.getByText('REQ-005@commerce-v1#0')).toBeInTheDocument();
});
test('impact suggestions are marked for review',async()=>{
 vi.mocked(api.impact).mockResolvedValue({change:'coupon',impacted_tests:[{test_id:'ECOM-005',title:'Expiry test',priority:'high',reason:'Expiry rule',citation_ids:[source.citation_id],registered_automation:true,needs_review:true}],sources:[source],embedding_mode:'demo',note:'Potential only'});
 mount(<RegressionImpact/>);fireEvent.click(screen.getByRole('button',{name:'Analyze regression impact'}));
 expect(await screen.findByText('ECOM-005: Expiry test')).toBeInTheDocument();
 expect(screen.getByText('high / Needs review / Registered automation')).toBeInTheDocument();
});
test('defect draft separates observation and hypothesis',async()=>{
 vi.mocked(api.drafts).mockResolvedValue([]);
 vi.mocked(api.analyze).mockResolvedValue({report_id:'d1',execution_id:'e1',mode:'demo',note:'Not confirmed',findings:[{test_id:'ECOM-005',title:'Expiry failure',classification:'potential_product_defect',observed:{name:'test_expired_coupon',status:'failed',message:'Expected 400 actual 200'},hypotheses:[{text:'Clock may differ',confidence:'low',citation_ids:[source.citation_id]}],next_steps:['Reproduce'],sources:[source],review_status:'draft',human_review_required:true}]});
 mount(<DefectIntelligence/>);fireEvent.change(screen.getByLabelText('Failed execution ID'),{target:{value:'e1'}});
 fireEvent.click(screen.getByRole('button',{name:'Analyze failure evidence'}));
 expect(await screen.findByText('Draft / Human review required')).toBeInTheDocument();
 expect(screen.getByText('Expected 400 actual 200')).toBeInTheDocument();
 expect(screen.getByText('Clock may differ')).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Export draft JSON'})).toBeInTheDocument();
});
test('invalid failure analysis shows error',async()=>{
 vi.mocked(api.drafts).mockResolvedValue([]);vi.mocked(api.analyze).mockRejectedValue(new Error('Execution has no failures'));
 mount(<DefectIntelligence/>);fireEvent.change(screen.getByLabelText('Failed execution ID'),{target:{value:'passed'}});
 fireEvent.click(screen.getByRole('button',{name:'Analyze failure evidence'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Execution has no failures');
});
test('retrieval evaluation displays actual recall and precision',async()=>{
 vi.mocked(api.status).mockResolvedValue({indexed_chunks:30,embedding_mode:'demo',embedding_model:'hash'});
 vi.mocked(api.evaluation).mockResolvedValue({queries:12,mean_recall_at_5:1,mean_precision_at_5:.2333,source_reference_percent:100,scope:'Synthetic only'});
 mount(<KnowledgeSearch/>);fireEvent.click(screen.getByRole('button',{name:'Load Recall@5 evaluation'}));
 expect(await screen.findByText('12 labeled queries / Recall@5 100.0% / Precision@5 23.3%')).toBeInTheDocument();
});
