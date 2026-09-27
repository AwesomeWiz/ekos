import { ArrowRight, BookOpen, Github, Hash, Layers, LoaderCircle, Puzzle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { PanelCard } from '../layout/RightPanel';
import { useAuth } from '../../hooks/useAuth';
import { useConnectors } from '../../hooks/useConnectors';
import { api, type GitHubSyncResult } from '../../services/api';

function syncLabel(value: string | null | undefined) {
  if (!value) return 'No sync recorded';
  const normalized = /Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? 'Sync time unavailable' : `Last synced ${date.toLocaleString()}`;
}
interface ActionState { pending: 'test' | 'sync' | null; message: string; error: boolean; result?: GitHubSyncResult }
const supportedTypes = ['GitHub', 'Jira', 'Confluence', 'Slack'];
const normalizedStatus = (status: string) => status.trim().toLowerCase().replace(/[\s-]+/g, '_');
const unconfiguredStatuses = new Set(['not_configured', 'unconfigured', 'missing_credentials']);
function stateLabel(status: string) {
  const value = normalizedStatus(status);
  if (['connected', 'synced', 'healthy', 'working', 'ok'].includes(value)) return 'Configured · Working';
  if (unconfiguredStatuses.has(value)) return 'Not configured';
  if (['error', 'failed', 'failing', 'unhealthy', 'disconnected', 'connection_error', 'sync_error', 'authentication_error', 'invalid_credentials'].includes(value)) return 'Configured · Unhealthy';
  return value === 'configured' ? 'Configured · Not yet verified' : 'Not yet verified';
}

export function ConnectedSources({ full = false }: { full?: boolean }) {
  const { profile, token, loading: authLoading, error: authError } = useAuth();
  const { connectors, loading, error, refresh } = useConnectors();
  const [actions, setActions] = useState<Record<string, ActionState>>({});
  const canTest = profile?.permissions?.some(permission => permission.resource === 'connectors' && permission.action === 'test') ?? false;
  const canSync = profile?.permissions?.some(permission => permission.resource === 'connectors' && permission.action === 'sync') ?? false;
  async function runAction(id: string, action: 'test' | 'sync') {
    if (!token || connectors.find(source => source.id === id)?.type.trim().toLowerCase() !== 'github') return;
    setActions(current => ({ ...current, [id]: { pending: action, message: '', error: false } }));
    try {
      if (action === 'test') {
        const result = await api.testConnector(token, id);
        if (result.status !== 'connected') throw new Error(`Connection test did not confirm a working connection (status: ${result.status || 'unknown'}).`);
        setActions(current => ({ ...current, [id]: { pending: null, message: `Connected as ${result.account}.`, error: false } }));
      } else {
        const result = await api.syncConnector(token, id);
        if (result.status !== 'success') throw new Error(`Sync did not complete successfully (status: ${result.status || 'unknown'}).`);
        setActions(current => ({ ...current, [id]: { pending: null, message: `Synced ${result.repository}.`, error: false, result } }));
      }
      refresh();
    } catch (reason) {
      setActions(current => ({ ...current, [id]: { pending: null, message: reason instanceof Error ? reason.message : 'The action failed.', error: true } }));
      refresh();
    }
  }
  return <PanelCard className="connected-sources-card"><div className="card-heading-row"><h2 className="card-heading">Connected Sources</h2>{profile && <button className="icon-button" aria-label="Refresh sources" title="Reload source status" disabled={loading} onClick={refresh}><RefreshCw size={16} /></button>}</div>
    {authLoading || loading ? <p className="state-message" role="status"><LoaderCircle className="spinner" size={16} />Loading sources…</p>
      : !profile ? <div className="state-message"><p>{authError || 'Sign in to view your connected sources.'}</p><Link to="/login" className="text-link">Sign in →</Link></div>
      : error ? <div className="state-message"><p role="alert">{error}</p><button className="text-link" onClick={refresh}>Try again</button></div>
      : connectors.length === 0 ? <p className="state-message">No connectors have been registered for your organization.</p>
      : <div className="source-list">{connectors.map(source => {
        const type = source.type.trim().toLowerCase();
        const Icon = ({ github: Github, jira: Layers, confluence: BookOpen, slack: Hash } as Record<string, typeof Github>)[type] || Puzzle;
        const action = actions[source.id];
        const configured = !unconfiguredStatuses.has(normalizedStatus(source.status));
        return <div className="connector-entry" key={source.id} role="group" aria-label={source.name}>
          <div className="connector-row"><span className="source-icon"><Icon size={20} /></span><div className="connector-copy"><p className="item-name">{source.name}</p><p className="item-meta">{source.type} · {stateLabel(source.status)}</p><p className="item-meta">{syncLabel(source.configuration?.last_sync)}</p></div><span className={`connection-state status-${source.status.toLowerCase().replace(/[^a-z]/g, '')}`}>{source.status.replaceAll('_', ' ')}</span></div>
          {full && type === 'github' && <div className="connector-actions">
            {canTest && <button type="button" disabled={!configured || !!action?.pending} title={configured ? 'Test the backend GitHub connection' : 'Configure GitHub on the backend first'} onClick={() => void runAction(source.id, 'test')}>{action?.pending === 'test' ? 'Testing…' : 'Test connection'}</button>}
            {canSync && <button type="button" disabled={!configured || !!action?.pending} title={configured ? 'Sync repository data' : 'Configure GitHub on the backend first'} onClick={() => void runAction(source.id, 'sync')}>{action?.pending === 'sync' ? 'Syncing…' : 'Sync'}</button>}
            {!canTest && !canSync && <span className="item-meta">Administrator permission is required to test or sync.</span>}
            {!configured && <span className="item-meta">Set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO on the backend.</span>}
          </div>}
          {full && type !== 'github' && <p className="item-meta action-result">Test/sync unavailable in this backend.</p>}
          {full && action?.message && <p className={action.error ? 'inline-error action-result' : 'state-message action-result'} role={action.error ? 'alert' : 'status'}>{action.message}</p>}
          {full && action?.result && <p className="item-meta action-result">Default branch: {action.result.default_branch} · {action.result.branches} branches · {action.result.commits} commits · {action.result.issues} issues</p>}
          {full && action?.result?.indexing && <p className={action.result.indexing.status === 'error' ? 'inline-error action-result' : 'item-meta action-result'} role={action.result.indexing.status === 'error' ? 'alert' : 'status'}>{action.result.indexing.status === 'error' ? action.result.indexing.error : `Indexed ${action.result.indexing.documents_indexed} documents · ${action.result.indexing.chroma_total} in your knowledge index`}</p>}
        </div>;
      })}</div>}
    {full && profile && !authLoading && !loading && !error && <div className="source-list">{supportedTypes.filter(type => !connectors.some(source => source.type.trim().toLowerCase() === type.toLowerCase())).map(type => {
      const Icon = ({ GitHub: Github, Jira: Layers, Confluence: BookOpen, Slack: Hash } as Record<string, typeof Github>)[type];
      return <div className="connector-entry" key={type} role="group" aria-label={type}><div className="connector-row"><span className="source-icon"><Icon size={20} /></span><div className="connector-copy"><p className="item-name">{type}</p><p className="item-meta">Supported · Not configured</p><p className="item-meta">No connector record registered.</p></div><span className="connection-state status-notconfigured">Not configured</span></div>
        <p className="item-meta action-result">{type === 'GitHub' ? 'Configure this connector on the backend.' : 'Test/sync unavailable in this backend.'}</p>
      </div>;
    })}</div>}
    {full ? <><p className="state-message connector-note">Statuses reflect backend records. Registered or active records are not proof of a working connection.</p><p className="item-meta planned-connectors">Supported connector types: {supportedTypes.join(' · ')}</p></> : <Link className="text-link card-footer-link" to="/connectors">View all sources <ArrowRight size={15} /></Link>}
  </PanelCard>;
}
