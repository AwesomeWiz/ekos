import { Link } from 'react-router-dom';
import { entities, entityHref, type EntityId } from '../../data/demoData';
import { EntityIcon } from '../EntityIcon';
import { PanelCard } from '../layout/RightPanel';

export function EntityRow({ id }: { id: EntityId }) {
  const entity = entities[id];
  return <Link to={entityHref(id)} className="entity-row"><span className={`entity-small-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} /></span><span><span className="item-name block">{entity.name}</span><span className="item-meta block">{entity.type}</span></span></Link>;
}
export function ContextSources({ sourceIds }: { sourceIds: EntityId[] }) {
  if (!sourceIds.length) return null;
  return <PanelCard className="context-card"><h2 className="card-heading">Sample context</h2><div className="section-label">Example sources <span className="count-badge">{sourceIds.length}</span></div><div className="entity-list">{sourceIds.map(id => <EntityRow key={id} id={id} />)}</div></PanelCard>;
}
