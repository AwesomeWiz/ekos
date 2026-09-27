// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import type { SearchResponse, SearchResult } from './services/api';

const profile = { id: 'search-user', full_name: 'Test Developer', email: 'dev@example.test', role: 'Developer', organization: 'Team', permissions: [{ resource: 'connectors', action: 'read' }] };
const result: SearchResult = { document_id: 'github:org:connector:team/demo:commit:abc123', text: 'Actual repository change: add Redis caching.', distance: 0.12,
  metadata: { source: 'github', repository: 'team/demo', entity_type: 'commit', entity_id: 'abc123', title: 'Add Redis caching', url: 'https://github.com/team/demo/commit/abc123' } };
beforeEach(() => { sessionStorage.clear(); sessionStorage.setItem('ekos.session-token', 'search-token'); Element.prototype.scrollIntoView = vi.fn(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function setup(search: () => Promise<Response>) {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith('/logout')) return Response.json({ message: 'ok' });
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer search-token');
    if (url.endsWith('/profile')) return Response.json(profile);
    if (url.endsWith('/connectors')) return Response.json([]);
    if (url.endsWith('/search')) return search();
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

describe('semantic retrieval chat', () => {
  it('sends the actual query, shows loading, renders real snippets and deduplicated context sources', async () => {
    let finish!: (response: Response) => void;
    const fetchMock = setup(() => new Promise(resolve => { finish = resolve; }));
    await openRoute();
    submit('Why was Redis introduced?');
    expect(within(screen.getByLabelText('Conversation')).getByText('Why was Redis introduced?')).toBeTruthy();
    expect(screen.getByText('Searching indexed knowledge…')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Send message' })).toHaveProperty('disabled', true);
    const response: SearchResponse = { query: 'Why was Redis introduced?', document_count: 4, results: [result, { ...result, document_id: `${result.document_id}:chunk:1`, text: 'Second chunk of this real commit.' }] };
    finish(Response.json(response));
    await screen.findByRole('heading', { name: 'Retrieved knowledge' });
    expect(screen.getByText(result.text)).toBeTruthy();
    const context = within(screen.getByRole('complementary', { name: 'Conversation context' }));
    expect(context.getAllByRole('link', { name: /Add Redis caching/ })).toHaveLength(1);
    expect(context.getByText('GitHub commit · team/demo')).toBeTruthy();
    expect(screen.queryByText('PAY-42')).toBeNull();
    expect(screen.queryByText('Architecture.md')).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/search', expect.objectContaining({ method: 'POST', body: JSON.stringify({ query: 'Why was Redis introduced?', top_k: 5 }) }));
  });

  it('stores retrieval history and submits follow-ups without rerunning completed searches', async () => {
    const fetchMock = setup(async () => Response.json({ query: 'Redis', results: [result], document_count: 1 }));
    await openRoute();
    submit('Redis');
    await screen.findByText(result.text);
    submit('Repository branches', 'Ask a follow-up...');
    await waitFor(() => expect(screen.getAllByText(result.text)).toHaveLength(2));
    const saved = JSON.parse(sessionStorage.getItem('ekos.chats.search-user')!);
    const route = `/chat/${saved[0].id}`;
    cleanup();
    await openRoute(route);
    expect(screen.getAllByText(result.text)).toHaveLength(2);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/search'))).toHaveLength(2);
  });

  it('keeps previously stored fixture answers labeled as samples', async () => {
    const fetchMock = setup(async () => { throw new Error('A completed sample must not trigger search'); });
    sessionStorage.setItem('ekos.chats.search-user', JSON.stringify([{ id: 'legacy', title: 'Old sample', turns: [{ id: 'old-turn', question: 'Old question', answer: 'Previously saved sample answer.', sourceIds: ['issue'], relatedIds: [] }] }]));
    await openRoute('/chat/legacy');
    expect(screen.getByText('Sample conversation')).toBeTruthy();
    expect(screen.getByText('Previously saved sample answer.')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/search'))).toHaveLength(0);
  });

  it('shows the empty-index message and connector link without sample references', async () => {
    setup(async () => Response.json({ query: 'Redis', results: [], document_count: 0 }));
    await openRoute(); submit('Redis');
    await screen.findByText('No indexed knowledge is available yet. Sync the GitHub connector first.');
    expect(screen.getByRole('link', { name: 'Open Connectors →' }).getAttribute('href')).toBe('/connectors');
    expect(screen.queryByRole('heading', { name: 'Sample context' })).toBeNull();
  });

  it('shows a no-match message when a populated index returns no results', async () => {
    setup(async () => Response.json({ query: 'Redis', results: [], document_count: 4 }));
    await openRoute(); submit('Redis');
    await screen.findByText('No indexed knowledge matched this query.');
  });

  it('shows API failures without substituting a sample answer', async () => {
    setup(async () => Response.json({ detail: 'Knowledge search is unavailable.' }, { status: 503 }));
    await openRoute(); submit('Redis');
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Knowledge search is unavailable.');
    expect(screen.queryByText('PAY-42')).toBeNull();
    fireEvent.change(screen.getByRole('textbox', { name: 'Ask a follow-up...' }), { target: { value: 'Retry search' } });
    expect(screen.getByRole('button', { name: 'Send message' })).toHaveProperty('disabled', false);
  });
});
