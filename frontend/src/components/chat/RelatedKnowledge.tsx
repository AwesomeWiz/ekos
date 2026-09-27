import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { EntityId } from '../../data/demoData';
import { EntityRow } from './ContextSources';
import { PanelCard } from '../layout/RightPanel';

export function RelatedKnowledge({ relatedIds }: { relatedIds: EntityId[] }) {
  return <PanelCard className="related-knowledge-card"><h2 className="card-heading">Sample knowledge</h2><div className="entity-list">{relatedIds.map(id => <EntityRow key={id} id={id} />)}</div><Link to="/knowledge-graph" className="text-link card-footer-link">View in graph <ArrowRight size={15} /></Link></PanelCard>;
}
