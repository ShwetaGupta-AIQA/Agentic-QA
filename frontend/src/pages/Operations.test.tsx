import {afterEach,expect,test,vi} from 'vitest';
import {render,screen} from '@testing-library/react';
import Operations from './Operations';
afterEach(()=>vi.unstubAllGlobals());
test('renders observed dependency modes and process scope',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({status:'ready',checks:{checkpoints:'postgresql',knowledge:'chroma-service',execution:'queue'}})}).mockResolvedValueOnce({ok:true,json:async()=>({counters:{http_request:8}})}));render(<Operations/>);
 expect(await screen.findByText('checkpoints: postgresql')).toBeInTheDocument();expect(screen.getByText('http_request: 8')).toBeInTheDocument();expect(screen.getByText(/Current API process only/)).toBeInTheDocument();
});
test('reports unavailable runtime without inventing healthy state',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:503}));render(<Operations/>);expect(await screen.findByRole('alert')).toHaveTextContent('503');expect(screen.queryByText('Status: ready')).not.toBeInTheDocument();});
