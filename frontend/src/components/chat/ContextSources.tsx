import { Link } from 'react-router-dom';
import { entities, entityHref, type EntityId } from '../../data/demoData';
import { EntityIcon } from '../EntityIcon';
import { PanelCard } from '../layout/RightPanel';
import { sourceUrl, type SearchResult } from '../../services/api';

export function EntityRow({ id }: { id: EntityId }) {
  const entity = entities[id];
  return <Link to={entityHref(id)} className="entity-row"><span className={`entity-small-icon type-${entity.type.toLowerCase().replaceAll(' ', '-')}`}><EntityIcon type={entity.type} /></span><span><span className="item-name block">{entity.name}</span><span className="item-meta block">{entity.type}</span></span></Link>;
}
export function ContextSources({ sourceIds, results }: { sourceIds: EntityId[]; results?: SearchResult[] }) {
  if (results !== undefined) {
    const sources = [...new Map(results.map(result => [`${result.metadata.repository}:${result.metadata.entity_type}:${result.metadata.entity_id}`, result])).values()];
    return <PanelCard className="context-card"><h2 className="card-heading">Context</h2><div className="section-label">Sources used <span className="count-badge">{sources.length}</span></div>
      {sources.length ? <div className="entity-list">{sources.map(source => {
        const content = <><span className="entity-small-icon"><EntityIcon type="GitHub Repository" /></span><span><span className="item-name block">{String(source.metadata.title || source.metadata.entity_id || 'GitHub knowledge')}</span><span className="item-meta block">GitHub {String(source.metadata.entity_type || 'document').replaceAll('_', ' ')} · {source.metadata.repository}</span></span></>;
        const url = sourceUrl(source);
        return url ? <a className="entity-row" key={source.document_id} href={url} target="_blank" rel="noopener noreferrer">{content}</a> : <div className="entity-row" key={source.document_id}>{content}</div>;
      })}</div> : <p className="state-message">No retrieved sources.</p>}
    </PanelCard>;
  }
  if (!sourceIds.length) return null;
  return <PanelCard className="context-card"><h2 className="card-heading">Sample context</h2><div className="section-label">Example sources <span className="count-badge">{sourceIds.length}</span></div><div className="entity-list">{sourceIds.map(id => <EntityRow key={id} id={id} />)}</div></PanelCard>;
}
