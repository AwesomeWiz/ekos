import { useEffect, useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { EntityDetails } from '../components/graph/EntityDetails';
import { GraphToolbar, graphTypes } from '../components/graph/GraphToolbar';
import { KnowledgeGraphCanvas } from '../components/graph/KnowledgeGraphCanvas';
import { useAuth } from '../hooks/useAuth';
import { api, type GraphResponse } from '../services/api';

export function KnowledgeGraphPage() {
  const { token, loading: restoring, error: sessionError } = useAuth();
  const [params, setParams] = useSearchParams();
  const [graph, setGraph] = useState<GraphResponse>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [query, setQuery] = useState('');
  const [types, setTypes] = useState<string[]>(graphTypes);
  const [hops, setHops] = useState(2);
  const [viewRevision, setViewRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setGraph({ nodes: [], edges: [] }); setError('');
    if (!token || restoring) { setLoading(false); return () => controller.abort(); }
    setLoading(true);
    void api.getGraph(token, controller.signal).then(value => {
      if (!controller.signal.aborted) setGraph(value);
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Knowledge graph is unavailable.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, restoring, revision]);
  const { nodes, edges } = token && !restoring ? graph : { nodes: [], edges: [] };
  const candidate = params.get('entity');
  const selected = nodes.find(node => node.id === candidate)?.id || nodes.find(node => node.type === 'GitHub Repository')?.id || nodes[0]?.id || '';
  const reachable = new Set([selected]);
  for (let depth = 0; depth < hops; depth++) {
    const previous = new Set(reachable);
    for (const edge of edges) {
      if (previous.has(edge.source)) reachable.add(edge.target);
      if (previous.has(edge.target)) reachable.add(edge.source);
    }
  }
  const visibleIds = nodes.filter(node => types.includes(node.type) && (query.trim() ? `${node.name} ${node.type} ${node.description}`.toLowerCase().includes(query.trim().toLowerCase()) : reachable.has(node.id))).map(node => node.id);
  const select = (id: string) => setParams({ entity: id }, { replace: true });
  return <AppShell className="graph-page" rightPanel={<EntityDetails selected={selected} nodes={nodes} edges={edges} onSelect={select} />}>
    <header className="graph-header"><h1>Knowledge Graph</h1><p>Explore how people, services, issues and documents are connected.</p></header>
    <GraphToolbar query={query} onQuery={setQuery} types={types} onTypes={setTypes} hops={hops} onHops={setHops} onReset={() => { setQuery(''); setTypes(graphTypes); setHops(2); setParams({}); setViewRevision(value => value + 1); }} />
    {restoring || loading ? <div className="graph-viewport"><p className="graph-empty" role="status"><span><LoaderCircle className="spinner" size={16} /> Loading knowledge graph...</span></p></div>
      : !token ? <div className="graph-viewport"><div className="graph-empty"><p>{sessionError || 'Sign in to view the knowledge graph.'} <Link className="text-link" to="/login">Sign in</Link></p></div></div>
      : error ? <div className="graph-viewport"><div className="graph-empty"><div><p className="inline-error" role="alert">{error}</p><button className="text-link" onClick={() => setRevision(value => value + 1)}>Try again</button></div></div></div>
      : !nodes.length ? <div className="graph-viewport"><div className="graph-empty"><div><p role="status">No GitHub graph data is available for your connected repositories.</p><button className="text-link" onClick={() => setRevision(value => value + 1)}>Try again</button></div></div></div>
      : <KnowledgeGraphCanvas key={viewRevision} nodes={nodes} edges={edges} selected={selected} visibleIds={visibleIds} onSelect={select} />}
    <div className="graph-bottom-bar"><span aria-live="polite">{visibleIds.length} entities - {query.trim() ? 'search results' : `within ${hops} ${hops === 1 ? 'hop' : 'hops'}`}</span></div>
  </AppShell>;
}
