import type { GraphNodeData } from '../../services/api';
import { EntityIcon } from '../EntityIcon';
import { graphNodeLabel } from './graphLabels';

export interface PositionedNode extends GraphNodeData { x: number; y: number }
export function GraphNode({ entity, selected, onSelect }: { entity: PositionedNode; selected: boolean; onSelect: () => void }) {
  const kind = entity.type === 'GitHub Repository' ? 'payment' : entity.type === 'Commit' ? 'document' : 'person';
  const label = graphNodeLabel(entity);
  const limit = entity.type === 'Commit' ? 36 : 24;
  return <button data-node-id={entity.id} className={`graph-node node-${kind} ${selected ? 'selected' : ''}`} style={{ left: `${entity.x / 760 * 100}%`, top: `${entity.y / 580 * 100}%` }} onClick={onSelect} aria-label={`${label}, ${entity.type}`} aria-pressed={selected} title={entity.description || label}>
    <span className={`node-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} size={kind === 'payment' ? 22 : 25} /></span>
    <span className="node-copy"><span className="node-name">{label.length > limit ? `${label.slice(0, limit - 1).trimEnd()}…` : label}</span><span className="node-type">{entity.type}</span></span>
  </button>;
}
