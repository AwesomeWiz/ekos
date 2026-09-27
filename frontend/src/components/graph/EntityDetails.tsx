import { BrandMark } from '../Brand';
import { entities, relationships, type EntityId } from '../../data/demoData';
import { useChat } from '../../hooks/useChat';
import { EntityIcon } from '../EntityIcon';
import { EntityRow } from '../chat/ContextSources';
import { PanelCard, RightPanel } from '../layout/RightPanel';

export function EntityDetails({ selected }: { selected: EntityId }) {
  const { startChat } = useChat();
  const entity = entities[selected];
  const entityRelationships = relationships.filter(edge => edge.from === selected || edge.to === selected);
  const connected: EntityId[] = entityRelationships.map(edge => edge.from === selected ? edge.to : edge.from);
  return <RightPanel label="Selected entity details"><PanelCard className="entity-details">
    <div className="entity-detail-heading"><span className={`detail-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} size={23} /></span><div><h2>{entity.name}</h2><p className="item-meta">{entity.type}</p></div></div>
    <p className="entity-description">{entity.description}</p>
    <div className="detail-section"><h3 className="section-label">Connected Entities <span className="count-badge">{connected.length}</span></h3><div className="entity-list">{connected.map(id => <EntityRow key={id} id={id} />)}</div></div>
    <div className="detail-section"><h3 className="section-label">Relationships</h3><dl className="relationship-list">{entityRelationships.map(edge => <div key={edge.label}><dt>{edge.label}</dt><dd>{entities[edge.from === selected ? edge.to : edge.from].name}</dd></div>)}</dl></div>
    <button className="primary-button" onClick={() => startChat(`Tell me about ${entity.name}.`)}><BrandMark />Ask EKOS about this</button>
  </PanelCard></RightPanel>;
}
