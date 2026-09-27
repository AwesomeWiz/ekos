// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, SESSION_EXPIRED_EVENT } from './api';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
describe('actual backend API contracts', () => {
  it('uses the JSON login contract and bearer authentication', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ access_token: 'token', token_type: 'bearer' })).mockResolvedValueOnce(Response.json([]));
    vi.stubGlobal('fetch', fetchMock);
    await api.login('user@example.test', 'typed-password');
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://127.0.0.1:8000/api/login', expect.objectContaining({ method: 'POST', body: JSON.stringify({ email: 'user@example.test', password: 'typed-password' }) }));
    await api.getConnectors('token');
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://127.0.0.1:8000/api/connectors', expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }));
  });
  it.each([403, 422, 500])('surfaces HTTP %s failures', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({}, { status })));
    await expect(api.getConnectors('token')).rejects.toMatchObject({ status });
  });
  it('uses protected semantic search and status endpoints', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ query: 'branches', results: [], document_count: 0 })).mockResolvedValueOnce(Response.json({ collection: 'enterprise_documents', document_count: 0, embedding_model: 'BAAI/bge-base-en-v1.5' }));
    vi.stubGlobal('fetch', fetchMock);
    await api.semanticSearch('token', 'branches', 3);
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://127.0.0.1:8000/api/search', expect.objectContaining({ method: 'POST', body: JSON.stringify({ query: 'branches', top_k: 3 }), headers: expect.objectContaining({ Authorization: 'Bearer token' }) }));
    await api.getSearchStatus('token');
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://127.0.0.1:8000/api/search/status', expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) }));
  });
  it('posts authenticated chat and allows time for local model generation', async () => {
    vi.useFakeTimers();
    let complete!: (response: Response) => void;
    const fetchMock = vi.fn(() => new Promise<Response>(resolve => { complete = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    const pending = api.chat('token', 'Hello');
    await vi.advanceTimersByTimeAsync(120000);
    expect(fetchMock.mock.calls[0]).toEqual(['http://127.0.0.1:8000/api/chat', expect.objectContaining({ method: 'POST', body: JSON.stringify({ message: 'Hello' }), headers: expect.objectContaining({ Authorization: 'Bearer token' }), signal: expect.objectContaining({ aborted: false }) })]);
    complete(Response.json({ answer: 'Hello', sources: [], graph_context: [] }));
    expect(await pending).toEqual({ answer: 'Hello', sources: [], graph_context: [] });
  });
  it('notifies session expiration only for protected requests', async () => {
    const listener = vi.fn(); window.addEventListener(SESSION_EXPIRED_EVENT, listener);
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => Response.json({}, { status: 401 })));
    try {
      await expect(api.login('user@example.test', 'wrong')).rejects.toMatchObject({ status: 401 });
      expect(listener).not.toHaveBeenCalled();
      await expect(api.getProfile('token')).rejects.toMatchObject({ status: 401 });
      expect(listener).toHaveBeenCalledOnce();
    } finally { window.removeEventListener(SESSION_EXPIRED_EVENT, listener); }
  });
  it('times out a hanging request and reports a network failure', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => new Promise((_resolve, reject) => options.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))));
    const result = expect(api.getConnectors('token')).rejects.toThrow('took too long');
    await vi.advanceTimersByTimeAsync(10000);
    await result;
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    await expect(api.getConnectors('token')).rejects.toThrow('Unable to reach the EKOS backend.');
  });
});
