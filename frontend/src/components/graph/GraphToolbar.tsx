import { useState } from 'react';
import { ListFilter, Network, RotateCcw, Search } from 'lucide-react';
import type { EntityType } from '../../data/demoData';

export const graphTypes: EntityType[] = ['Service', 'Technology', 'Person', 'Jira Issue', 'Document', 'GitHub Repository'];
interface GraphToolbarProps {
  query: string; onQuery: (value: string) => void;
  types: EntityType[]; onTypes: (value: EntityType[]) => void;
  hops: number; onHops: (value: number) => void;
  onReset: () => void;
}
export function GraphToolbar({ query, onQuery, types, onTypes, hops, onHops, onReset }: GraphToolbarProps) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  return <div className="graph-toolbar">
    <label className="graph-search"><Search size={17} aria-hidden="true" /><input placeholder="Search the knowledge graph..." aria-label="Search the knowledge graph" value={query} onChange={event => onQuery(event.target.value)} /></label>
    <div className="filter-control"><button className={`toolbar-button ${types.length < graphTypes.length ? 'filter-active' : ''}`} aria-expanded={filtersOpen} aria-controls="graph-filters" onClick={() => setFiltersOpen(open => !open)}><ListFilter size={15} />Filter{types.length < graphTypes.length && <span>({types.length})</span>}</button>
      {filtersOpen && <fieldset id="graph-filters" className="filter-popover"><legend>Entity types</legend>{graphTypes.map(type => <label key={type}><input type="checkbox" checked={types.includes(type)} onChange={() => onTypes(types.includes(type) ? types.filter(item => item !== type) : [...types, type])} />{type}</label>)}</fieldset>}
    </div>
    <span className="hop-control"><Network aria-hidden="true" /><select className="toolbar-button hop-select" aria-label="Relationship hops" value={hops} onChange={event => onHops(Number(event.target.value))}><option value="1">1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option></select></span>
    <button className="toolbar-button reset-button" onClick={() => { onReset(); setFiltersOpen(false); }}><RotateCcw size={15} /><span>Reset view</span></button>
  </div>;
}
