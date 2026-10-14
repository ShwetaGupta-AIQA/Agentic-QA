import {afterEach,expect,test,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import SelfHealing from './SelfHealing';
import * as api from '../services/healingApi';
vi.mock('../services/healingApi',()=>({history:vi.fn(),demonstrate:vi.fn(),validate:vi.fn(),decision:vi.fn(),evidence:vi.fn(()=>'/artifact'),mcpTools:vi.fn(),mcpCall:vi.fn()}));
const proposal={proposal_id:'p1',status:'proposed',target:'coupon',original_locator:{kind:'css',value:'#apply-coupon'},original_hash:'hash',baseline:{validation_id:'v0',candidate:'baseline',passed:false,category:'locator_not_found'},candidates:[{id:'role_coupon',locator:{kind:'role',role:'button',name:'Apply coupon'},matches:1,reason:'Unique button'}],note:'Validate first'};
const validated={...proposal,status:'validated',selected_candidate:'role_coupon',validation:{validation_id:'v1',candidate:'role_coupon',passed:true,category:'passed',matches:1},patch_preview:'locator-only diff'};
afterEach(()=>vi.clearAllMocks());
test('source application is disabled until validation and explicit human review',async()=>{
 vi.mocked(api.history).mockResolvedValue([]);vi.mocked(api.demonstrate).mockResolvedValue(proposal);vi.mocked(api.validate).mockResolvedValue(validated);
 render(<SelfHealing/>);fireEvent.click(screen.getByRole('button',{name:'Reproduce and propose repair'}));
 await screen.findByText('Proposal p1');expect(screen.getByRole('button',{name:'Approve and apply locator patch'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Validate full coupon test'}));await screen.findByText('locator-only diff');
 fireEvent.change(screen.getByLabelText('Reviewer name'),{target:{value:'Reviewer'}});
 expect(screen.getByRole('button',{name:'Approve and apply locator patch'})).toBeDisabled();
 fireEvent.click(screen.getByLabelText('I reviewed the patch and passing full-test evidence and approve this locator-only change'));
 expect(screen.getByRole('button',{name:'Approve and apply locator patch'})).toBeEnabled();
 expect(api.decision).not.toHaveBeenCalled();
});
test('rejection calls the explicit reject action',async()=>{
 vi.mocked(api.history).mockResolvedValue([]);vi.mocked(api.demonstrate).mockResolvedValue(proposal);vi.mocked(api.decision).mockResolvedValue({...proposal,status:'rejected'});
 render(<SelfHealing/>);fireEvent.click(screen.getByRole('button',{name:'Reproduce and propose repair'}));await screen.findByText('Proposal p1');
 fireEvent.change(screen.getByLabelText('Reviewer name'),{target:{value:'Reviewer'}});fireEvent.click(screen.getByRole('button',{name:'Reject proposal'}));
 expect(await screen.findByText('Status: rejected')).toBeInTheDocument();
 expect(api.decision).toHaveBeenCalledWith('p1','reject','Reviewer','',false);
});
test('shows MCP tools as read-only with no patch operation',async()=>{
 vi.mocked(api.history).mockResolvedValue([]);vi.mocked(api.mcpTools).mockResolvedValue({tools:[{name:'get_execution',description:'Read result',scope:'executions:read',input_schema:{}}],resources:['qa://policy'],transport:'private stdio',authentication:'session capability',patch_tools:false});
 render(<SelfHealing/>);fireEvent.click(screen.getByRole('button',{name:'Connect and inspect MCP tools'}));
 expect(await screen.findByText('private stdio / session capability / Patch tools: none')).toBeInTheDocument();
});
test('validation errors remain visible without applying changes',async()=>{
 vi.mocked(api.history).mockResolvedValue([]);vi.mocked(api.demonstrate).mockRejectedValue(new Error('Browser unavailable'));
 render(<SelfHealing/>);fireEvent.click(screen.getByRole('button',{name:'Reproduce and propose repair'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Browser unavailable');expect(api.decision).not.toHaveBeenCalled();
});
