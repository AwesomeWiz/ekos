import { BrandMark } from '../Brand';
import type { GraphEdgeData, GraphNodeData } from '../../services/api';
import { useChat } from '../../hooks/useChat';
import { EntityIcon } from '../EntityIcon';
import { PanelCard, RightPanel } from '../layout/RightPanel';
import { graphNodeLabel } from './graphLabels';

export function EntityDetails({ selected, nodes, edges, onSelect }: { selected: string; nodes: GraphNodeData[]; edges: GraphEdgeData[]; onSelect: (id: string) => void }) {
  const { startChat } = useChat();
  const entity = nodes.find(node => node.id === selected);
  const entityRelationships = edges.filter(edge => edge.source === selected || edge.target === selected);
  const connectedIds = new Set(entityRelationships.map(edge => edge.source === selected ? edge.target : edge.source));
  const connected = nodes.filter(node => connectedIds.has(node.id));
  return <RightPanel label="Selected entity details"><PanelCard className="entity-details">
    {!entity ? <p className="state-message">Select an entity to view its details.</p> : <>
      <div className="entity-detail-heading"><span className={`detail-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} size={23} /></span><div><h2>{graphNodeLabel(entity)}</h2><p className="item-meta">{entity.type}</p></div></div>
      {entity.type === 'Commit' && <p className="item-meta">Commit SHA: {entity.id.replace(/^Commit:/, '')}</p>}
      {entity.description && <p className="entity-description">{entity.description}</p>}
      <div className="detail-section"><h3 className="section-label">Connected Entities <span className="count-badge">{connected.length}</span></h3><div className="entity-list">{connected.map(node => <button className="entity-row" key={node.id} onClick={() => onSelect(node.id)}><span className="entity-small-icon"><EntityIcon type={node.type} /></span><span><span className="item-name block">{node.name}</span><span className="item-meta block">{node.type}</span></span></button>)}</div></div>
      <div className="detail-section"><h3 className="section-label">Relationships</h3><dl className="relationship-list">{entityRelationships.map((edge, index) => <div key={index}><dt>{edge.relationship}</dt><dd>{nodes.find(node => node.id === (edge.source === selected ? edge.target : edge.source))?.name}</dd></div>)}</dl></div>
      <button className="primary-button" onClick={() => startChat(`Tell me about ${entity.name}.`)}><BrandMark />Ask EKOS about this</button>
    </>}
  </PanelCard></RightPanel>;
}
