// These contracts mirror backend/schemas and the routes registered in backend/main.py.
export interface TokenResponse { access_token: string; token_type: string }
export interface UserProfile { id: string; full_name: string; email: string; role: string | null; organization: string | null; permissions: { resource: string; action: string }[] }
export interface Connector {
  id: string; name: string; type: string; status: string;
  organization_id: string | null; created_at: string;
  configuration: { id: string; connector_id: string; api_url: string | null; sync_interval: string | null; last_sync: string | null } | null;
}
export interface ConnectorTestResult { status: string; connector: string; account?: string | null; details?: string | null }
export interface IndexingSummary { status: 'indexed' | 'error'; documents_indexed: number; chroma_total: number | null; error: string | null }
export interface ConnectorSyncResult { status: string; connector: string; repository?: string | null; default_branch?: string | null; branches?: number | null; commits?: number | null; issues?: number | null; synced_at?: string | null; records_processed?: number; documents_indexed?: number; graph_nodes_updated?: number; indexing?: IndexingSummary | null }
export interface SearchResult { document_id: string; text: string; metadata: Record<string, string | number | boolean>; distance: number }
export interface SearchResponse { query: string; results: SearchResult[]; document_count: number }
export interface SearchStatus { collection: string; document_count: number; embedding_model: string }
export interface ManagedUser { id: string; full_name: string; email: string; role_id: string | null; organization_id: string | null; status: boolean; created_at: string }
export interface UserRole { id: string; role_name: string }
export interface GraphNodeData { id: string; name: string; type: string; description: string }
export interface GraphEdgeData { source: string; target: string; relationship: string }
export interface GraphResponse { nodes: GraphNodeData[]; edges: GraphEdgeData[] }
interface GraphApiResponse { nodes: { id: string; label: string; type: 'User' | 'Commit' | 'Repository' | 'Issue'; description?: string }[]; edges: GraphEdgeData[] }
const graphDisplayTypes = { User: 'Person', Commit: 'Commit', Repository: 'GitHub Repository', Issue: 'Jira Issue' };

export interface NewUser { full_name: string; email: string; password: string; role_id: string }

export interface ChatSource { title?: string | null; source?: string | null; connector?: string | null; entity_type?: string | null; type?: string | null; url?: string | null; repository?: string | null; snippet: string }
export interface GraphRelationship { source: string; relationship: string; target: string }
export interface ChatResponse { answer: string; sources: ChatSource[]; graph_context: GraphRelationship[] }
export function chatSourceUrl(source: ChatSource): string | undefined {
  return sourceUrl({ document_id: '', text: '', distance: 0, metadata: { url: source.url || '' } });
}

export function sourceUrl(result: SearchResult): string | undefined {
  const value = result.metadata.url;
  if (typeof value !== 'string') return undefined;
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined; } catch { return undefined; }
}

export class ApiError extends Error {
  constructor(message: string, public status = 0) { super(message); this.name = 'ApiError'; }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const prefix = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '');
export const SESSION_EXPIRED_EVENT = 'ekos:session-expired';

interface RequestOptions { method?: 'GET' | 'POST' | 'PUT'; body?: unknown; token?: string; signal?: AbortSignal; timeoutMs?: number }
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) controller.abort();
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, options.timeoutMs ?? 10000);
  try {
    const response = await fetch(`${baseUrl}${prefix}${path}`, {
      method: options.method || 'GET', signal: controller.signal,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}) },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => null) as { detail?: unknown } | null)?.detail;
      if (response.status === 401 && options.token) window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, { detail: options.token }));
      if (response.status === 401) throw new ApiError(options.token ? 'Your session has expired. Please sign in again.' : 'Incorrect email or password.', 401);
      if (response.status === 403) throw new ApiError('Your account does not have access to this resource.', 403);
      if (response.status === 422) throw new ApiError('Please check the information you entered.', 422);
      throw new ApiError(typeof detail === 'string' ? detail : `The EKOS backend could not complete this request (${response.status}). Please try again.`, response.status);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (options.signal?.aborted) throw error;
    if (timedOut) throw new ApiError('The EKOS backend took too long to respond. Please try again.');
    throw new ApiError('Unable to reach the EKOS backend.');
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener('abort', abort);
  }
}

export const api = {
  getGraph: (token: string, signal?: AbortSignal) => request<GraphApiResponse>('/graph', { token, signal, timeoutMs: 15000 }).then(response => ({
    nodes: response.nodes.map(node => ({ id: node.id, name: node.label, type: graphDisplayTypes[node.type], description: node.description || '' })),
    edges: response.edges,
  })),
  getUsers: (token: string, signal?: AbortSignal) => request<ManagedUser[]>('/users', { token, signal }),
  getUserRoles: (token: string, signal?: AbortSignal) => request<UserRole[]>('/users/roles', { token, signal }),
  createUser: (token: string, body: NewUser, signal?: AbortSignal) => request<ManagedUser>('/users', { method: 'POST', token, body, signal }),
  updateUser: (token: string, id: string, body: { role_id?: string; status?: boolean }, signal?: AbortSignal) => request<ManagedUser>(`/users/${encodeURIComponent(id)}`, { method: 'PUT', token, body, signal }),
  chat: (token: string, message: string, signal?: AbortSignal) => request<ChatResponse>('/chat', { method: 'POST', token, body: { message }, signal, timeoutMs: 180000 }),
  login: (email: string, password: string) => request<TokenResponse>('/login', { method: 'POST', body: { email, password } }),
  logout: () => request<{ message: string; details: string }>('/logout', { method: 'POST' }),
  getProfile: (token: string, signal?: AbortSignal) => request<UserProfile>('/profile', { token, signal }),
  getConnectors: (token: string, signal?: AbortSignal) => request<Connector[]>('/connectors', { token, signal }),
  testConnector: (token: string, id: string) => request<ConnectorTestResult>(`/connectors/${encodeURIComponent(id)}/test`, { method: 'POST', token, timeoutMs: 20000 }),
  syncConnector: (token: string, id: string) => request<ConnectorSyncResult>(`/connectors/${encodeURIComponent(id)}/sync`, { method: 'POST', token, timeoutMs: 300000 }),
  semanticSearch: (token: string, query: string, topK = 5, signal?: AbortSignal) => request<SearchResponse>('/search', { method: 'POST', token, body: { query, top_k: topK }, signal, timeoutMs: 120000 }),
  getSearchStatus: (token: string, signal?: AbortSignal) => request<SearchStatus>('/search/status', { token, signal }),
};
