import { afterEach, expect, test, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

const run = {run_id: 'run-1', requirement: 'Apply coupon during checkout', mode: 'demo', status: 'awaiting_approval', analysis: {scenarios: ['Reject expired coupon'], ambiguities: ['Clarify expiry'], risks: ['Incorrect discount'], summary: 'Demo analysis'}};
const mount = (path = '/requirements') => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
const response = (body: unknown, ok = true, status = 200) => ({ok, status, json: async () => body});
afterEach(() => vi.unstubAllGlobals());

test('dashboard preserves five metrics and demo executions', () => {
  mount('/');
  expect(screen.getByText('Automation Coverage')).toBeInTheDocument();
  expect(screen.getByText('Recent Test Executions')).toBeInTheDocument();
  expect(screen.getByText('Release Readiness Agent')).toBeInTheDocument();
});
test('renders the agent workspace', () => {
  mount();
  expect(screen.getByLabelText('E-commerce requirement')).toBeInTheDocument();
  expect(screen.queryByRole('button', {name: 'Approve analysis'})).not.toBeInTheDocument();
});
test('blocks whitespace', () => {
  mount();
  fireEvent.change(screen.getByLabelText('E-commerce requirement'), {target: {value: ' '.repeat(20)}});
  expect(screen.getByRole('button', {name: 'Run Requirements Agent'})).toBeDisabled();
});
for (const decision of ['approve', 'reject'] as const) {
  test(`human can ${decision} a pending analysis`, async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(run)).mockResolvedValueOnce(response({...run, decision, status: decision === 'approve' ? 'approved' : 'rejected'}));
    vi.stubGlobal('fetch', fetchMock);
    mount();
    fireEvent.click(screen.getByRole('button', {name: 'Run Requirements Agent'}));
    expect(await screen.findByText('Reject expired coupon')).toBeInTheDocument();
    expect(screen.getByText('Clarify expiry')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', {name: decision === 'approve' ? 'Approve analysis' : 'Reject analysis'}));
    expect(await screen.findByText(decision === 'approve' ? 'approved' : 'rejected')).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({decision});
    expect(screen.queryByRole('button', {name: 'Approve analysis'})).not.toBeInTheDocument();
  });
}
test('editing input removes approval for the old result', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(run)));
  mount();
  fireEvent.click(screen.getByRole('button', {name: 'Run Requirements Agent'}));
  await screen.findByText('Reject expired coupon');
  fireEvent.change(screen.getByLabelText('E-commerce requirement'), {target: {value: 'Add items to shopping cart'}});
  expect(screen.queryByLabelText('Agent results')).not.toBeInTheDocument();
});
test('agent failure permits retry', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({detail: 'Agent execution failed'}, false, 502)));
  mount();
  fireEvent.click(screen.getByRole('button', {name: 'Run Requirements Agent'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('502');
  expect(screen.getByRole('button', {name: 'Run Requirements Agent'})).toBeEnabled();
});
test('failed approval retains review and allows retry', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(run)).mockRejectedValueOnce(new Error('Network unavailable')));
  mount();
  fireEvent.click(screen.getByRole('button', {name: 'Run Requirements Agent'}));
  fireEvent.click(await screen.findByRole('button', {name: 'Approve analysis'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable');
  expect(screen.getByRole('button', {name: 'Approve analysis'})).toBeEnabled();
});
