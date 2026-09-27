import { useRef, useState, type PointerEvent } from 'react';
import { Minus, Plus } from 'lucide-react';
import type { GraphEdgeData, GraphNodeData } from '../../services/api';
import { GraphNode } from './GraphNode';

export function KnowledgeGraphCanvas({ nodes, edges, selected, visibleIds, onSelect }: { nodes: GraphNodeData[]; edges: GraphEdgeData[]; selected: string; visibleIds: string[]; onSelect: (id: string) => void }) {
  const viewport = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [dragging, setDragging] = useState(false);
  const suppressClick = useRef(false);
  const gesture = useRef<{ pointerId: number; x: number; y: number; view: typeof view; nodeId?: string; position?: { x: number; y: number }; width: number; height: number; moved: boolean } | null>(null);
  const commits = nodes.filter(node => node.type === 'Commit');
  const repositories = nodes.filter(node => node.type === 'GitHub Repository');
  const others = nodes.filter(node => node.type !== 'Commit' && node.type !== 'GitHub Repository');
  const angles = new Map(commits.map((node, index) => [node.id, -Math.PI / 2 + index * Math.PI * 2 / Math.max(1, commits.length)]));
  const positioned = nodes.map(node => {
    if (positions[node.id]) return { ...node, ...positions[node.id] };
    if (node.id === repositories[0]?.id) return { ...node, x: 380, y: 290 };
    const related = edges.filter(edge => edge.source === node.id && angles.has(edge.target)).map(edge => angles.get(edge.target)!);
    const angle = angles.get(node.id) ?? (related.length ? Math.atan2(related.reduce((sum, value) => sum + Math.sin(value), 0), related.reduce((sum, value) => sum + Math.cos(value), 0)) : others.indexOf(node) * Math.PI * 2 / Math.max(1, others.length));
    const outer = node.type !== 'Commit';
    return { ...node, x: 380 + (outer ? 315 : 210) * Math.cos(angle), y: 290 + (outer ? 235 : 130) * Math.sin(angle) };
  });
  const visibleNodes = positioned.filter(node => visibleIds.includes(node.id));
  const visibleEdges = edges.filter(edge => visibleIds.includes(edge.source) && visibleIds.includes(edge.target)).flatMap(edge => {
    const from = positioned.find(node => node.id === edge.source);
    const to = positioned.find(node => node.id === edge.target);
    return from && to ? [{ ...edge, from, to, key: JSON.stringify([edge.source, edge.relationship, edge.target]) }] : [];
  });
  const zoom = (change: number) => setView(previous => {
    const scale = Math.min(2.5, Math.max(0.5, Math.round((previous.scale + change) * 100) / 100));
    const centerX = (viewport.current?.clientWidth || 760) / 2;
    const centerY = (viewport.current?.clientHeight || 580) / 2;
    return { scale, x: centerX - (centerX - previous.x) * scale / previous.scale, y: centerY - (centerY - previous.y) * scale / previous.scale };
  });
  const start = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || gesture.current) return;
    const button = (event.target as Element).closest('button');
    const nodeId = button?.dataset.nodeId;
    if (button && !nodeId) return;
    const node = positioned.find(value => value.id === nodeId);
    suppressClick.current = false;
    gesture.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, view, nodeId,
      position: node && { x: node.x, y: node.y }, width: canvas.current?.offsetWidth || 760,
      height: canvas.current?.offsetHeight || 580, moved: false };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDragging(true);
  };
  const move = (event: PointerEvent<HTMLDivElement>) => {
    const active = gesture.current;
    if (!active || active.pointerId !== event.pointerId) return;
    const dx = event.clientX - active.x, dy = event.clientY - active.y;
    if (!active.moved && Math.hypot(dx, dy) < 4) return;
    active.moved = true;
    if (active.nodeId && active.position) {
      const { nodeId, position } = active;
      setPositions(values => ({ ...values, [nodeId]: {
        x: position.x + dx / active.view.scale * 760 / active.width,
        y: position.y + dy / active.view.scale * 580 / active.height,
      } }));
    } else setView({ ...active.view, x: active.view.x + dx, y: active.view.y + dy });
  };
  const end = (event: PointerEvent<HTMLDivElement>) => {
    const active = gesture.current;
    if (!active || active.pointerId !== event.pointerId) return;
    suppressClick.current = event.type === 'pointerup' && (active.moved || !!active.nodeId);
    if (active.nodeId && event.type === 'pointerup') onSelect(active.nodeId);
    gesture.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };
  return <div ref={viewport} className={`graph-viewport readable-graph interactive-graph ${dragging ? 'dragging' : ''}`}
    onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerCancel={end} onLostPointerCapture={end}
    onClickCapture={event => { if (suppressClick.current && event.detail !== 0) { suppressClick.current = false; event.preventDefault(); event.stopPropagation(); } }}>
    <div className="graph-zoom-controls" role="group" aria-label="Graph zoom controls">
      <button className="toolbar-button" aria-label="Zoom out" disabled={view.scale <= 0.5} onClick={() => zoom(-0.2)}><Minus size={15} /></button>
      <span className="item-meta" aria-live="polite">{Math.round(view.scale * 100)}%</span>
      <button className="toolbar-button" aria-label="Zoom in" disabled={view.scale >= 2.5} onClick={() => zoom(0.2)}><Plus size={15} /></button>
    </div>
    <div ref={canvas} className="graph-canvas" role="group" aria-label="GitHub knowledge graph" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`, transformOrigin: '0 0' }}>
    <svg className="graph-edges" viewBox="0 0 760 580" preserveAspectRatio="none" aria-hidden="true">
      {visibleEdges.map(edge => <line key={edge.key} x1={edge.from.x} y1={edge.from.y} x2={edge.to.x} y2={edge.to.y} stroke="#586C5B" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />)}
    </svg>
    {visibleEdges.map(edge => {
      const dx = edge.to.x - edge.from.x, dy = edge.to.y - edge.from.y;
      const length = Math.hypot(dx, dy) || 1;
      const midpoint = { x: (edge.from.x + edge.to.x) / 2, y: (edge.from.y + edge.to.y) / 2 };
      // Include the pill's approximate half-size and a small gap around the repository card.
      const repository = visibleNodes.find(node => node.type === 'GitHub Repository'
        && Math.abs(midpoint.x - node.x) < 123 && Math.abs(midpoint.y - node.y) < 62);
      const direction = repository && ((midpoint.x - repository.x) * -dy + (midpoint.y - repository.y) * dx < 0) ? -1 : 1;
      const offset = repository ? 12 * direction : 0;
      const x = midpoint.x - dy / length * offset;
      const y = midpoint.y + dx / length * offset;
      return <span key={edge.key} className="graph-edge-label" style={{ left: `${x / 760 * 100}%`, top: `${y / 580 * 100}%` }}>{edge.relationship}</span>;
    })}
    {visibleNodes.map(entity => <GraphNode key={entity.id} entity={entity} selected={selected === entity.id} onSelect={() => onSelect(entity.id)} />)}
    {visibleNodes.length === 0 && <p className="graph-empty" role="status">No matching entities. Try another search or reset the view.</p>}
  </div></div>;
}
