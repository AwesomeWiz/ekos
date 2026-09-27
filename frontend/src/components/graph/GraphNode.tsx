import type { GraphEntity } from '../../data/demoData';
import { EntityIcon } from '../EntityIcon';
import { Box } from 'lucide-react';

export function GraphNode({ entity, selected, onSelect }: { entity: GraphEntity; selected: boolean; onSelect: () => void }) {
  return <button className={`graph-node node-${entity.id} ${selected ? 'selected' : ''}`} style={{ left: `${entity.x / 760 * 100}%`, top: `${entity.y / 580 * 100}%` }} onClick={onSelect} aria-label={`${entity.name}, ${entity.type}`} aria-pressed={selected}>
    <span className={`node-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}>{entity.id === 'auth' ? <Box size={25} aria-hidden="true" /> : <EntityIcon type={entity.type} size={entity.id === 'payment' ? 22 : 25} />}</span>
    <span className="node-copy"><span className="node-name">{entity.name}</span><span className="node-type">{entity.type}</span></span>
  </button>;
}
