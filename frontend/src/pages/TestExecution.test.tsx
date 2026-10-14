import {afterEach,expect,test,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import TestExecution from './TestExecution';
import * as api from '../services/executionApi';
vi.mock('../services/executionApi',()=>({suites:vi.fn(),history:vi.fn(),execute:vi.fn(),execution:vi.fn(),artifactUrl:vi.fn(()=>'/evidence')}));
const catalog=[{id:'ECOM-001',title:'Add product',types:['UI'],automation_count:1,contract_version:'commerce-v1'}];
const done={execution_id:'e-1',status:'passed',test_ids:['ECOM-001'],passed:1,failed:0,errors:0,skipped:0,duration_seconds:1,results:[],artifacts:['junit.xml'],message:'Real result'};
const mount=(path='/executions')=>render(<MemoryRouter initialEntries={[path]}><TestExecution/></MemoryRouter>);
afterEach(()=>vi.clearAllMocks());
function setup(){vi.mocked(api.suites).mockResolvedValue(catalog);vi.mocked(api.history).mockResolvedValue([]);}
test('execution requires selected suites and explicit approval',async()=>{
 setup();mount();await screen.findByText(/ECOM-001: Add product/);
 const button=screen.getByRole('button',{name:'Execute approved tests'});expect(button).toBeDisabled();
 fireEvent.click(screen.getByLabelText(/ECOM-001: Add product/));expect(button).toBeDisabled();
 fireEvent.click(screen.getByLabelText('I reviewed these selected registered suites and approve local execution'));expect(button).toBeEnabled();
 fireEvent.click(screen.getByLabelText(/ECOM-001: Add product/));expect(button).toBeDisabled();
});
test('submits registered IDs and shows actual execution evidence',async()=>{
 setup();vi.mocked(api.execute).mockResolvedValue(done);vi.mocked(api.execution).mockResolvedValue(done);mount();
 fireEvent.click(await screen.findByLabelText(/ECOM-001: Add product/));
 fireEvent.click(screen.getByLabelText('I reviewed these selected registered suites and approve local execution'));
 fireEvent.click(screen.getByRole('button',{name:'Execute approved tests'}));
 expect(await screen.findByText('Status: passed')).toBeInTheDocument();expect(api.execute).toHaveBeenCalledWith(['ECOM-001']);
 expect(screen.getByRole('link',{name:'junit.xml'})).toBeInTheDocument();
});
test('shows failure classification without calling it a defect',async()=>{
 setup();vi.mocked(api.execution).mockResolvedValue({...done,status:'failed',passed:0,failed:1,results:[{test_id:'ECOM-001',name:'test_add',type:'UI',status:'failed',classification:'product_assertion',message:'Expected product in cart'}]});mount('/executions?execution=e-1');
 expect(await screen.findByText('product_assertion')).toBeInTheDocument();expect(screen.getByText('Expected product in cart')).toBeInTheDocument();
});
test('displays API errors',async()=>{
 setup();vi.mocked(api.suites).mockRejectedValue(new Error('Unavailable'));mount();expect(await screen.findByRole('alert')).toHaveTextContent('Unavailable');
});
