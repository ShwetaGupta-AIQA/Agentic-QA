import {afterEach,expect,test,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import ReleaseReadiness from './ReleaseReadiness';
import * as api from '../services/releaseApi';
vi.mock('../services/releaseApi',()=>({API:'http://localhost:8001',history:vi.fn(),reviews:vi.fn(),reviewer:vi.fn(),policy:vi.fn(),assess:vi.fn(),attest:vi.fn(),decide:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
function setup(recommendation:'GO'|'CONDITIONAL_GO'|'NO_GO'='NO_GO',available=true){
 const record={assessment_id:'a',release_id:'commerce-1.0.0',assessment_hash:'hash',status:'awaiting_review',approval_available:available,evaluation:{recommendation,pass_rate:null,risk_score:null,gates:[],conditions:['Review risk']},aggregate:{evidence:{requirement_coverage:null,critical_defects_open:null,high_defects_open:null},sources:[],coverage_definition:'Mapped execution coverage',aggregation_note:'Missing evidence is unknown'},explanation:{summary:'Gate recommendation'}} as unknown as api.Assessment;
 vi.mocked(api.history).mockResolvedValue([record]);vi.mocked(api.reviews).mockResolvedValue([]);vi.mocked(api.reviewer).mockResolvedValue({reviewer:'local-reviewer',configured:true,scope:'local'});vi.mocked(api.policy).mockResolvedValue({});
 render(<ReleaseReadiness/>);return record;
}
async function select(){fireEvent.click(await screen.findByRole('button',{name:/commerce-1.0.0: /}));}
function credentials(){fireEvent.change(screen.getByLabelText('Release reviewer credential'),{target:{value:'x'.repeat(40)}});fireEvent.change(screen.getByLabelText(/Decision rationale/),{target:{value:'Reviewed all evidence'}});}
test('missing evidence remains unknown and NO-GO cannot authorize',async()=>{setup();await select();expect(screen.getByText('Pass rate: Unknown')).toBeInTheDocument();credentials();expect(screen.getByRole('button',{name:'Authorize recommended release decision'})).toBeDisabled();});
test('GO requires reviewer credentials',async()=>{setup('GO');await select();expect(screen.getByRole('button',{name:'Authorize recommended release decision'})).toBeDisabled();credentials();expect(screen.getByRole('button',{name:'Authorize recommended release decision'})).toBeEnabled();expect(localStorage.length).toBe(0);});
test('expired checkpoint prevents authorization',async()=>{setup('GO',false);await select();credentials();expect(screen.getByRole('button',{name:'Authorize recommended release decision'})).toBeDisabled();expect(screen.getByText(/Backend checkpoint expired/)).toBeInTheDocument();});
test('changing release clears prior assessment',async()=>{setup('GO');await select();fireEvent.change(screen.getByLabelText('Release ID'),{target:{value:'new-release'}});expect(screen.queryByRole('region',{name:'Release assessment'})).not.toBeInTheDocument();});

test('conditional recommendation requires explicit acknowledgement',async()=>{setup('CONDITIONAL_GO');await select();credentials();const button=screen.getByRole('button',{name:'Authorize recommended release decision'});expect(button).toBeDisabled();fireEvent.click(screen.getByLabelText('I acknowledge the listed release conditions'));expect(button).toBeEnabled();});
