import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { EntityDetails } from '../components/graph/EntityDetails';
import { GraphToolbar, graphTypes } from '../components/graph/GraphToolbar';
import { KnowledgeGraphCanvas } from '../components/graph/KnowledgeGraphCanvas';
import { entities, graphNodes, neighborhood, type EntityId, type EntityType } from '../data/demoData';

export function KnowledgeGraphPage() {
  const [params, setParams] = useSearchParams();
  const candidate = params.get('entity');
  const selected: EntityId = candidate && Object.hasOwn(entities, candidate) ? candidate as EntityId : 'payment';
  const [query, setQuery] = useState('');
  const [types, setTypes] = useState<EntityType[]>(graphTypes);
  const [hops, setHops] = useState(2);
  const reachable = neighborhood(selected, hops);
  // Search spans the sample graph; without search the hop radius follows the selected node.
  const visibleIds = graphNodes.filter(node => types.includes(node.type) && (query.trim() ? `${node.name} ${node.type}`.toLowerCase().includes(query.trim().toLowerCase()) : reachable.has(node.id))).map(node => node.id);
  return <AppShell className="graph-page" rightPanel={<EntityDetails selected={selected} />}>
    <header className="graph-header"><h1>Knowledge Graph <span className="demo-badge">Sample data</span></h1><p>Explore how people, services, issues and documents are connected.</p></header>
    <GraphToolbar query={query} onQuery={setQuery} types={types} onTypes={setTypes} hops={hops} onHops={setHops} onReset={() => { setQuery(''); setTypes(graphTypes); setHops(2); setParams({}); }} />
    <KnowledgeGraphCanvas selected={selected} visibleIds={visibleIds} onSelect={id => setParams({ entity: id }, { replace: true })} />
    <div className="graph-bottom-bar"><span aria-live="polite">{visibleIds.length} entities · {query.trim() ? 'search results' : `within ${hops} ${hops === 1 ? 'hop' : 'hops'} of ${entities[selected].name}`}</span></div>
  </AppShell>;
}
