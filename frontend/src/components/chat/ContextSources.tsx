import { Link } from 'react-router-dom';
import { entities, entityHref, type EntityId } from '../../data/demoData';
import { EntityIcon } from '../EntityIcon';
import { ConnectorLogo } from '../ConnectorLogo';
import { PanelCard } from '../layout/RightPanel';
import { chatSourceUrl, type ChatSource } from '../../services/api';

export function EntityRow({ id }: { id: EntityId }) {
  const entity = entities[id];
  return <Link to={entityHref(id)} className="entity-row"><span className={`entity-small-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} /></span><span><span className="item-name block">{entity.name}</span><span className="item-meta block">{entity.type}</span></span></Link>;
}
export function ContextSources({ sources, loading = false }: { sources: ChatSource[]; loading?: boolean }) {
  const unique = [...new Map(sources.map(source => [JSON.stringify([source.url, source.repository, source.title, source.entity_type, source.source]), source])).values()];
  return <PanelCard className="context-card"><h2 className="card-heading">Context</h2><div className="section-label">Sources used <span className="count-badge">{unique.length}</span></div>
    {unique.length ? <div className="entity-list">{unique.map((source, index) => {
      const kind = (source.source || source.connector || '').trim().toLowerCase();
      const content = <><span className="entity-small-icon" role="img" aria-label={`${kind || 'Unknown'} source`}><ConnectorLogo type={kind} /></span><span><span className="item-name block">{source.title || source.repository || 'Knowledge source'}</span><span className="item-meta block">{[source.source || source.connector, source.entity_type || source.type, source.repository].filter(Boolean).join(' · ')}</span></span></>;
      const url = chatSourceUrl(source);
      return url ? <a className="entity-row" key={index} href={url} target="_blank" rel="noopener noreferrer">{content}</a> : <div className="entity-row" key={index}>{content}</div>;
    })}</div> : <p className="state-message">{loading ? 'Retrieving context…' : 'No retrieved sources.'}</p>}
  </PanelCard>;
}
