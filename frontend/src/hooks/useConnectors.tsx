import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, type Connector } from '../services/api';
import { useAuth } from './useAuth';

interface ConnectorState { connectors: Connector[]; loading: boolean; error: string; refresh: () => void }
const ConnectorsContext = createContext<ConnectorState | null>(null);
export function ConnectorsProvider({ children }: { children: ReactNode }) {
  const { token, profile } = useAuth();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    setConnectors([]); setError('');
    if (!token || !profile) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    api.getConnectors(token, controller.signal).then(data => {
      if (!controller.signal.aborted) setConnectors(data);
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to load sources.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, profile, revision]);
  return <ConnectorsContext.Provider value={{ connectors: profile ? connectors : [], loading, error, refresh: () => setRevision(value => value + 1) }}>{children}</ConnectorsContext.Provider>;
}
export function useConnectors() {
  const context = useContext(ConnectorsContext);
  if (!context) throw new Error('useConnectors requires ConnectorsProvider');
  return context;
}
