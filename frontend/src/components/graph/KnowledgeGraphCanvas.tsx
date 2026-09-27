import { graphNodes, relationships, type EntityId } from '../../data/demoData';
import { GraphNode } from './GraphNode';

export function KnowledgeGraphCanvas({ selected, visibleIds, onSelect }: { selected: EntityId; visibleIds: EntityId[]; onSelect: (id: EntityId) => void }) {
  const visibleNodes = graphNodes.filter(node => visibleIds.includes(node.id));
  return <div className="graph-viewport"><div className="graph-canvas" role="group" aria-label="Payment Service knowledge graph">
    <svg className="graph-edges" viewBox="0 0 760 580" preserveAspectRatio="none" aria-hidden="true">
      {relationships.filter(edge => visibleIds.includes(edge.from) && visibleIds.includes(edge.to)).map(edge => {
        const from = graphNodes.find(node => node.id === edge.from)!;
        const to = graphNodes.find(node => node.id === edge.to)!;
        return <line key={edge.label} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#586C5B" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />;
      })}
    </svg>
    {relationships.filter(edge => visibleIds.includes(edge.from) && visibleIds.includes(edge.to)).map(edge => <span key={edge.label} className="graph-edge-label" style={{ left: `${edge.x / 760 * 100}%`, top: `${edge.y / 580 * 100}%` }}>{edge.label}</span>)}
    {visibleNodes.map(entity => <GraphNode key={entity.id} entity={entity} selected={selected === entity.id} onSelect={() => onSelect(entity.id)} />)}
    {visibleNodes.length === 0 && <p className="graph-empty" role="status">No matching entities. Try another search or reset the view.</p>}
  </div></div>;
}
