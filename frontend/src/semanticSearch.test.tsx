// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
const profile = { id: 'search-user', full_name: 'Test Developer', email: 'dev@example.test', role: 'Developer', organization: 'Team', permissions: [{ resource: 'connectors', action: 'read' }] };
const source = { title: 'Add Redis caching', source: 'github', repository: 'team/demo', entity_type: 'commit', url: 'https://github.com/team/demo/commit/abc123', snippet: 'Actual repository change: add Redis caching.' };
const response = { answer: 'Redis reduces database load.', sources: [source, source], graph_context: [{ source: 'Developer', relationship: 'COMMITTED', target: 'abc123' }] };
beforeEach(() => { sessionStorage.clear(); sessionStorage.setItem('ekos.session-token', 'search-token'); Element.prototype.scrollIntoView = vi.fn(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function setup(search: () => Promise<Response>) {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith('/logout')) return Response.json({ message: 'ok' });
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer search-token');
    if (url.endsWith('/profile')) return Response.json(profile);
    if (url.endsWith('/connectors')) return Response.json([]);
    if (url.endsWith('/chat')) return search();
    throw new Error(`Unexpected endpoint ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
async function openRoute(route = '/') {
  render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>);
  await screen.findByText('Test Developer');
}
function submit(query: string, placeholder = 'Ask EKOS anything...') {
  fireEvent.change(screen.getByRole('textbox', { name: placeholder }), { target: { value: query } });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
}

describe('backend chat', () => {
  it('posts the message with JWT, shows thinking, then renders answer and deduplicated source context', async () => {
    let finish!: (response: Response) => void;
    const fetchMock = setup(() => new Promise(resolve => { finish = resolve; }));
    await openRoute(); submit('Why was Redis introduced?');
    expect(within(screen.getByLabelText('Conversation')).getByText('Why was Redis introduced?')).toBeTruthy();
    expect(screen.getByRole('status').textContent).toContain('Thinking');
    expect(screen.getByRole('button', { name: 'Send message' })).toHaveProperty('disabled', true);
    finish(Response.json(response));
    await screen.findByText(response.answer);
    expect(screen.getAllByText(source.snippet)).toHaveLength(2);
    const context = within(screen.getByRole('complementary', { name: 'Conversation context' }));
    expect(context.getAllByRole('link', { name: /Add Redis caching/ })).toHaveLength(1);
    expect(screen.queryByText('PAY-42')).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/chat', expect.objectContaining({ method: 'POST', body: JSON.stringify({ message: 'Why was Redis introduced?' }), headers: expect.objectContaining({ Authorization: 'Bearer search-token' }) }));
    expect(screen.getByRole('textbox', { name: 'Ask a follow-up...' })).toHaveProperty('maxLength', 2000);
  });
  it('persists answers and graph context, submits follow-ups, and restores without repeating requests', async () => {
    const fetchMock = setup(async () => Response.json(response));
    await openRoute(); submit('Redis'); await screen.findByText(response.answer);
    submit('Repository branches', 'Ask a follow-up...');
    await waitFor(() => expect(screen.getAllByText(response.answer)).toHaveLength(2));
    const saved = JSON.parse(sessionStorage.getItem('ekos.chats.search-user')!);
    expect(saved[0].turns[0].graphContext).toEqual(response.graph_context);
    cleanup(); await openRoute(`/chat/${saved[0].id}`);
    expect(screen.getAllByText(response.answer)).toHaveLength(2);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/chat'))).toHaveLength(2);
  });
  it('disables legacy sample histories', async () => {
    setup(async () => { throw new Error('No request expected'); });
    sessionStorage.setItem('ekos.chats.search-user', JSON.stringify([{ id: 'legacy', title: 'Old sample', turns: [{ id: 'old', question: 'Old question', answer: 'Fake answer', sourceIds: ['issue'], relatedIds: [] }] }]));
    await openRoute('/chat/legacy');
    expect(screen.getByRole('heading', { name: 'Conversation not found' })).toBeTruthy();
    expect(screen.queryByText('Fake answer')).toBeNull();
  });
  it('renders an answer without sources or graph results', async () => {
    setup(async () => Response.json({ answer: 'Information was not found.', sources: [], graph_context: [] }));
    await openRoute(); submit('Unknown'); await screen.findByText('Information was not found.');
    expect(screen.queryByRole('heading', { name: 'Sources' })).toBeNull();
    expect(screen.getByText('No retrieved sources.')).toBeTruthy();
  });
  it.each([503, 403])('shows HTTP %s errors and allows another question', async status => {
    setup(async () => Response.json({ detail: 'Ollama is unavailable.' }, { status }));
    await openRoute(); submit('Redis');
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', status === 403 ? 'Your account does not have access to this resource.' : 'Ollama is unavailable.');
    expect(screen.queryByText(response.answer)).toBeNull();
    submit('Retry', 'Ask a follow-up...');
    await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(2));
  });
  it('shows a network failure', async () => {
    setup(async () => { throw new TypeError('offline'); });
    await openRoute(); submit('Redis');
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Unable to reach the EKOS backend.');
  });
  it('expires the existing auth session on a chat 401', async () => {
    setup(async () => Response.json({ detail: 'expired' }, { status: 401 }));
    await openRoute(); submit('Redis');
    await screen.findByText('Your session has expired. Please sign in again.');
    expect(sessionStorage.getItem('ekos.session-token')).toBeNull();
  });
});
