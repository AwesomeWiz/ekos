// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { App } from './App';

beforeEach(() => {
  vi.stubGlobal('innerWidth', 1366);
  sessionStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function LocationProbe() { return <output data-testid="route">{useLocation().pathname}</output>; }
function openRoute(route = '/') { return render(<MemoryRouter initialEntries={[route]}><App /><LocationProbe /></MemoryRouter>); }
function submit(question: string, placeholder = 'Ask EKOS anything...') {
  fireEvent.change(screen.getByRole('textbox', { name: placeholder }), { target: { value: question } });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
}
const profile = { id: 'user-one', full_name: 'Test Developer', email: 'developer@example.test', role: 'Developer', organization: 'Test team', permissions: [{ resource: 'connectors', action: 'read' }] };
const connector = { id: 'connector-one', name: 'Team repository', type: 'GitHub', status: 'paused', organization_id: 'org-one', created_at: '2026-01-01T10:00:00Z', configuration: { id: 'config-one', connector_id: 'connector-one', api_url: null, sync_interval: '1 hour', last_sync: null } };
function mockApi() {
  return vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith('/login')) return Response.json({ access_token: 'test-token', token_type: 'bearer' });
    if (url.endsWith('/logout')) return Response.json({ message: 'Logged out', details: 'Stateless JWT' });
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer test-token');
    if (url.endsWith('/profile')) return Response.json(profile);
    if (url.endsWith('/connectors')) return Response.json([connector]);
    throw new Error(`Unexpected endpoint: ${url}`);
  });
}
async function signIn() {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: profile.email } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'entered-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  await screen.findByText('Team repository');
}

describe('complete demo flows', () => {
  it('keeps anonymous chat usable without inventing source status', () => {
    openRoute();
    expect(screen.getByRole('heading', { name: /Good (morning|afternoon|evening), there\./ })).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Send message' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText('Sign in to view your connected sources.')).toBeTruthy();
    expect(screen.queryByText('Up to date')).toBeNull();
    expect(screen.queryByText('Payment service ownership')).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('does not seed a fake conversation', () => {
    openRoute('/chat/redis');
    expect(screen.getByRole('heading', { name: 'Conversation not found' })).toBeTruthy();
    expect(screen.queryByText('Sample conversation')).toBeNull();
  });

  it('preserves follow-ups, switches history, and restores after remount', async () => {
    openRoute();
    submit('Explain Redis caching');
    await screen.findByText('Sign in to chat with your indexed knowledge.');
    const route = screen.getByTestId('route').textContent!;
    submit('Who works on this service?', 'Ask a follow-up...');
    await waitFor(() => expect(screen.getAllByText('Sign in to chat with your indexed knowledge.')).toHaveLength(2));
    fireEvent.click(screen.getByRole('link', { name: 'New chat' }));
    expect((screen.getByRole('textbox', { name: 'Ask EKOS anything...' }) as HTMLTextAreaElement).value).toBe('');
    submit('What is the weather?');
    await screen.findByText('Sign in to chat with your indexed knowledge.');
    expect(screen.queryByRole('heading', { name: 'Sample context' })).toBeNull();
    fireEvent.click(screen.getByRole('link', { name: 'Explain Redis caching' }));
    expect(screen.getByText('Who works on this service?')).toBeTruthy();
    cleanup();
    openRoute(route);
    expect(screen.getByText('Who works on this service?')).toBeTruthy();
    expect(screen.getAllByText('Sign in to chat with your indexed knowledge.')).toHaveLength(2);
  });

  it('sends suggested questions automatically and supports Enter submission', async () => {
    openRoute();
    fireEvent.click(screen.getByRole('button', { name: 'Who owns the payment service?' }));
    await screen.findByText('Sign in to chat with your indexed knowledge.');
    expect(within(screen.getByLabelText('Conversation')).getByText('Who owns the payment service?')).toBeTruthy();
    const input = screen.getByRole('textbox', { name: 'Ask a follow-up...' });
    fireEvent.change(input, { target: { value: 'Find architecture docs' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(within(screen.getByLabelText('Conversation')).queryByText('Find architecture docs')).toBeNull();
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(screen.getAllByText('Sign in to chat with your indexed knowledge.')).toHaveLength(2));
  });

  it('requires sign-in to view real graph data without showing sample entities', () => {
    openRoute('/knowledge-graph');
    expect(screen.getByText('Sign in to view the knowledge graph.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Payment Service, Service' })).toBeNull();
  });

  it('loads API connector statuses, refreshes them, and signs out', async () => {
    const fetchMock = mockApi(); vi.stubGlobal('fetch', fetchMock);
    openRoute('/login');
    await signIn();
    expect(screen.getByText('paused')).toBeTruthy();
    expect(screen.getByText('No sync recorded')).toBeTruthy();
    expect(screen.getByText('Test Developer')).toBeTruthy();
    expect(screen.getByText('Administrator permission is required to test or sync.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Sync' })).toBeNull();
    fireEvent.click(screen.getByRole('link', { name: 'Account' }));
    expect(screen.getByText(profile.email)).toBeTruthy();
    expect(screen.getByText('Test team')).toBeTruthy();
    expect(screen.getByText('connectors: read')).toBeTruthy();
    fireEvent.click(screen.getByRole('link', { name: 'Connectors' }));
    expect(sessionStorage.getItem('ekos.session-token')).toBe('test-token');
    expect(JSON.stringify(sessionStorage)).not.toContain('entered-password');
    fetchMock.mockResolvedValueOnce(Response.json([]));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
    await screen.findByText(/No connectors have been registered for your organization/);
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(sessionStorage.getItem('ekos.session-token')).toBeNull();
    expect(screen.queryByText('Test Developer')).toBeNull();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/logout'), expect.anything()));
  });

  it('shows administrator grants and runs test/sync with loading and server results', async () => {
    const admin = { ...profile, id: 'admin-one', full_name: 'System Admin', email: 'admin@example.test', role: 'Administrator', permissions: [
      { resource: 'connectors', action: 'read' }, { resource: 'connectors', action: 'manage' },
      { resource: 'connectors', action: 'test' }, { resource: 'connectors', action: 'sync' },
    ] };
    let status = 'configured';
    let completeSync!: (value: Response) => void;
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith('/login')) return Response.json({ access_token: 'test-token', token_type: 'bearer' });
      if (url.endsWith('/logout')) return Response.json({ message: 'ok' });
      if (url.endsWith('/profile')) return Response.json(admin);
      if (url.endsWith('/connectors') && !url.endsWith('/sync')) return Response.json([{ ...connector, status }]);
      if (url.endsWith('/test')) { status = 'connected'; return Response.json({ status, connector: 'GitHub', account: 'demo-member' }); }
      if (url.endsWith('/sync')) return await new Promise<Response>(resolve => { completeSync = resolve; });
      throw new Error(`Unexpected API call ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    openRoute('/login');
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: admin.email } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'typed-value' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByText('Team repository');
    fireEvent.click(screen.getByRole('link', { name: 'Account' }));
    expect(screen.getByText('connectors: sync')).toBeTruthy();
    fireEvent.click(screen.getByRole('link', { name: 'Connectors' }));
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText('Connected as demo-member.');
    await screen.findByText('connected');
    fireEvent.click(screen.getByRole('button', { name: 'Sync' }));
    expect(screen.getByRole('button', { name: 'Syncing…' })).toHaveProperty('disabled', true);
    completeSync(Response.json({ status: 'success', connector: 'GitHub', repository: 'team/demo', default_branch: 'main', branches: 2, commits: 3, issues: 1, synced_at: '2026-01-01T10:00:00Z' }));
    await screen.findByText('Synced team/demo.');
    expect(screen.getByText(/2 branches · 3 commits · 1 issues/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/connectors/connector-one/sync'), expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) }));
  });

  it('restores a session and expires it on a protected 401', async () => {
    sessionStorage.setItem('ekos.session-token', 'test-token');
    const fetchMock = mockApi(); vi.stubGlobal('fetch', fetchMock);
    openRoute('/connectors');
    await screen.findByText('Team repository');
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'expired' }, { status: 401 }));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
    await screen.findByText('Your session has expired. Please sign in again.');
    expect(sessionStorage.getItem('ekos.session-token')).toBeNull();
    expect(screen.queryByText('Team repository')).toBeNull();
  });

  it('shows forbidden, network, and retry states without fake connector rows', async () => {
    vi.stubGlobal('fetch', mockApi()); openRoute('/login'); await signIn();
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(Response.json({}, { status: 403 }));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Your account does not have access to this resource.');
    fetchMock.mockRejectedValueOnce(new TypeError('offline'));
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Unable to reach the EKOS backend.');
    expect(screen.queryByText('Team repository')).toBeNull();
    fetchMock.mockResolvedValueOnce(Response.json([connector]));
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Team repository');
  });

  it('handles incorrect login and invalid or missing local data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({}, { status: 401 })));
    openRoute('/login');
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: profile.email } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'incorrect' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByText('Incorrect email or password.');
    expect(sessionStorage.getItem('ekos.session-token')).toBeNull();
    cleanup(); sessionStorage.setItem('ekos.chats.guest', '{invalid json');
    openRoute('/chat/missing');
    expect(screen.getByRole('heading', { name: 'Conversation not found' })).toBeTruthy();
    cleanup(); openRoute('/knowledge-graph?entity=__proto__');
    expect(screen.getByText('Sign in to view the knowledge graph.')).toBeTruthy();
  });
});
