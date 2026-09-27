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
const stateLabel = (status: string) => status === 'synced' || status === 'connected' ? 'Connected' : status === 'not_configured' ? 'Not configured' : status === 'error' ? 'Connection error' : 'Not yet verified';

export function ConnectedSources({ full = false }: { full?: boolean }) {
  const { profile, token, loading: authLoading, error: authError } = useAuth();
  const { connectors, loading, error, refresh } = useConnectors();
  const [actions, setActions] = useState<Record<string, ActionState>>({});
  const canTest = profile?.permissions?.some(permission => permission.resource === 'connectors' && permission.action === 'test') ?? false;
  const canSync = profile?.permissions?.some(permission => permission.resource === 'connectors' && permission.action === 'sync') ?? false;
  async function runAction(id: string, action: 'test' | 'sync') {
    if (!token) return;
    setActions(current => ({ ...current, [id]: { pending: action, message: '', error: false } }));
    try {
      if (action === 'test') {
        const result = await api.testConnector(token, id);
        setActions(current => ({ ...current, [id]: { pending: null, message: `Connected as ${result.account}.`, error: false } }));
      } else {
        const result = await api.syncConnector(token, id);
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
      : connectors.length === 0 ? <p className="state-message">No connectors have been registered for your organization. Run the demo seed command on the backend.</p>
      : <div className="source-list">{connectors.map(source => {
        const Icon = ({ github: Github, jira: Layers, confluence: BookOpen, slack: Hash } as Record<string, typeof Github>)[source.type.toLowerCase()] || Puzzle;
        const action = actions[source.id];
        const configured = source.status !== 'not_configured';
        return <div className="connector-entry" key={source.id}>
          <div className="connector-row"><span className="source-icon"><Icon size={20} /></span><div className="connector-copy"><p className="item-name">{source.name}</p><p className="item-meta">{source.type} · {stateLabel(source.status)}</p><p className="item-meta">{syncLabel(source.configuration?.last_sync)}</p></div><span className={`connection-state status-${source.status.toLowerCase().replace(/[^a-z]/g, '')}`}>{source.status.replaceAll('_', ' ')}</span></div>
          {full && source.type.toLowerCase() === 'github' && <div className="connector-actions">
            {canTest && <button type="button" disabled={!configured || !!action?.pending} title={configured ? 'Test the backend GitHub connection' : 'Configure GitHub on the backend first'} onClick={() => void runAction(source.id, 'test')}>{action?.pending === 'test' ? 'Testing…' : 'Test connection'}</button>}
            {canSync && <button type="button" disabled={!configured || !!action?.pending} title={configured ? 'Sync repository data' : 'Configure GitHub on the backend first'} onClick={() => void runAction(source.id, 'sync')}>{action?.pending === 'sync' ? 'Syncing…' : 'Sync'}</button>}
            {!canTest && !canSync && <span className="item-meta">Administrator permission is required to test or sync.</span>}
            {!configured && <span className="item-meta">Set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO on the backend.</span>}
          </div>}
          {full && action?.message && <p className={action.error ? 'inline-error action-result' : 'state-message action-result'} role={action.error ? 'alert' : 'status'}>{action.message}</p>}
          {full && action?.result && <p className="item-meta action-result">Default branch: {action.result.default_branch} · {action.result.branches} branches · {action.result.commits} commits · {action.result.issues} issues</p>}
        </div>;
      })}</div>}
    {full ? <><p className="state-message connector-note">Statuses reflect registered records. Only a successful test or sync verifies a GitHub connection.</p><p className="item-meta planned-connectors">Planned: Jira · Slack · Confluence</p></> : <Link className="text-link card-footer-link" to="/connectors">View all sources <ArrowRight size={15} /></Link>}
  </PanelCard>;
}
