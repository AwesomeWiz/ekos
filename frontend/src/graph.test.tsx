// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { GraphNode } from './components/graph/GraphNode';

const graph = { nodes: [
  { id: 'Repository:team/ekos', label: 'ekos', type: 'Repository', description: 'team/ekos' },
  { id: 'Commit:abc', label: 'abc', type: 'Commit', description: 'Add Redis caching' },
  { id: 'User:developer', label: 'Contributor', type: 'User', description: '' },
], edges: [
  { source: 'Commit:abc', target: 'Repository:team/ekos', relationship: 'BELONGS_TO' },
  { source: 'User:developer', target: 'Commit:abc', relationship: 'COMMITTED' },
] };
beforeEach(() => {
  vi.stubGlobal('innerWidth', 1366);
  sessionStorage.clear(); sessionStorage.setItem('ekos.session-token', 'graph-token');
  vi.stubGlobal('PointerEvent', class extends MouseEvent {
    pointerId: number;
    constructor(type: string, init: PointerEventInit = {}) { super(type, init); this.pointerId = init.pointerId ?? 1; }
  });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function setup(response: () => Promise<Response>, route = '/knowledge-graph') {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer graph-token');
    if (url.endsWith('/profile')) return Response.json({ id: 'graph-user', full_name: 'Graph Developer', role: 'Developer', permissions: [{ resource: 'connectors', action: 'read' }] });
    if (url.endsWith('/connectors')) return Response.json([]);
    if (url.endsWith('/graph')) return response();
    throw new Error(`Unexpected endpoint ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>);
  return fetchMock;
}
describe('real knowledge graph', () => {
  it('truncates commit subjects, preserves full text in the tooltip, and falls back to SHA', () => {
    const message = 'Improve repository indexing with permission scoped retrieval and caching';
    const props = { selected: false, onSelect: vi.fn() };
    const { rerender } = render(<GraphNode {...props} entity={{ id: 'Commit:abc123', name: 'abc123', type: 'Commit', description: `${message}\nAdditional details`, x: 200, y: 100 }} />);
    const button = screen.getByRole('button', { name: `${message}, Commit` });
    expect(button.title).toContain('Additional details');
    expect(button.querySelector('.node-name')?.textContent).toBe(`${message.slice(0, 35).trimEnd()}…`);
    rerender(<GraphNode {...props} entity={{ id: 'Commit:abc123', name: 'abc123', type: 'Commit', description: '  ', x: 200, y: 100 }} />);
    expect(screen.getByRole('button', { name: 'abc123, Commit' })).toBeTruthy();
  });
  it('loads with JWT and reuses selection, details, search, filters, hops and reset', async () => {
    let finish!: (response: Response) => void;
    const fetchMock = setup(() => new Promise(resolve => { finish = resolve; }), '/knowledge-graph?entity=__proto__');
    await screen.findByText('Loading knowledge graph...');
    await waitFor(() => expect(typeof finish).toBe('function'));
    finish(Response.json(graph));
    let canvas = within(await screen.findByRole('group', { name: 'GitHub knowledge graph' }));
    expect(canvas.getAllByRole('button')).toHaveLength(3);
    expect(canvas.getByRole('button', { name: 'ekos, GitHub Repository' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.queryByText('Payment Service')).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/graph', expect.objectContaining({ method: 'GET' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Relationship hops' }), { target: { value: '1' } });
    expect(canvas.getAllByRole('button')).toHaveLength(2);
    fireEvent.click(canvas.getByRole('button', { name: 'Add Redis caching, Commit' }));
    expect(within(screen.getByRole('complementary', { name: 'Selected entity details' })).getByRole('heading', { name: 'Add Redis caching' })).toBeTruthy();
    expect(screen.getByText('Commit SHA: abc')).toBeTruthy();
    expect(canvas.getAllByRole('button')).toHaveLength(3);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search the knowledge graph' }), { target: { value: 'Contributor' } });
    expect(canvas.getAllByRole('button')).toHaveLength(1);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search the knowledge graph' }), { target: { value: 'missing' } });
    expect(canvas.getByRole('status').textContent).toContain('No matching entities');
    fireEvent.click(screen.getByRole('button', { name: 'Reset view' }));
    canvas = within(screen.getByRole('group', { name: 'GitHub knowledge graph' }));
    expect(canvas.getAllByRole('button')).toHaveLength(3);
    fireEvent.click(screen.getByRole('button', { name: 'Filter' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Person' }));
    expect(canvas.getAllByRole('button')).toHaveLength(2);
  });
  it('zooms, pans, drags nodes with connected edges, and resets spatial state', async () => {
    setup(async () => Response.json(graph));
    const canvas = await screen.findByRole('group', { name: 'GitHub knowledge graph' });
    const viewport = canvas.parentElement!;
    const node = within(canvas).getByRole('button', { name: 'Add Redis caching, Commit' });
    const initialLeft = node.style.left;
    const initialEdge = canvas.querySelector('line')!.getAttribute('x1');
    const assertLabelsFollowEdges = () => {
      const lines = [...canvas.querySelectorAll('.graph-edges line')];
      const labels = [...canvas.querySelectorAll<HTMLElement>('.graph-edge-label')];
      expect(labels).toHaveLength(lines.length);
      lines.forEach((line, index) => {
        const x1 = Number(line.getAttribute('x1')), y1 = Number(line.getAttribute('y1'));
        const x2 = Number(line.getAttribute('x2')), y2 = Number(line.getAttribute('y2'));
        const x = parseFloat(labels[index].style.left) * 760 / 100;
        const y = parseFloat(labels[index].style.top) * 580 / 100;
        const offsetX = x - (x1 + x2) / 2, offsetY = y - (y1 + y2) / 2;
        expect(Math.hypot(offsetX, offsetY)).toBeLessThanOrEqual(12.00001);
        // Any adjustment must be perpendicular, never shift the pill along another edge.
        expect(offsetX * (x2 - x1) + offsetY * (y2 - y1)).toBeCloseTo(0, 5);
      });
    };
    assertLabelsFollowEdges();
    const initialLabelPositions = [...canvas.querySelectorAll<HTMLElement>('.graph-edge-label')].map(label => label.style.cssText);
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(canvas.style.transform).toContain('scale(1.2)');
    const zoomedTransform = canvas.style.transform;
    fireEvent.pointerDown(viewport, { pointerId: 1, button: 0, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(viewport, { pointerId: 1, clientX: 70, clientY: 50 });
    fireEvent.pointerUp(viewport, { pointerId: 1 });
    expect(canvas.style.transform).not.toBe(zoomedTransform);
    assertLabelsFollowEdges();
    expect([...canvas.querySelectorAll<HTMLElement>('.graph-edge-label')].map(label => label.style.cssText)).toEqual(initialLabelPositions);
    const pannedTransform = canvas.style.transform;
    fireEvent.pointerDown(node, { pointerId: 2, button: 0, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(viewport, { pointerId: 2, clientX: 160, clientY: 130 });
    fireEvent.pointerUp(viewport, { pointerId: 2 });
    expect(node.style.left).not.toBe(initialLeft);
    expect(canvas.querySelector('line')!.getAttribute('x1')).not.toBe(initialEdge);
    assertLabelsFollowEdges();
    expect([...canvas.querySelectorAll<HTMLElement>('.graph-edge-label')].map(label => label.style.cssText)).not.toEqual(initialLabelPositions);
    expect(canvas.style.transform).toBe(pannedTransform);
    expect(node.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByText('Commit SHA: abc')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reset view' }));
    const resetCanvas = screen.getByRole('group', { name: 'GitHub knowledge graph' });
    expect(resetCanvas.style.transform).toBe('translate(0px, 0px) scale(1)');
    expect(within(resetCanvas).getByRole('button', { name: 'Add Redis caching, Commit' }).style.left).toBe(initialLeft);
    expect(within(resetCanvas).getByRole('button', { name: 'ekos, GitHub Repository' }).getAttribute('aria-pressed')).toBe('true');
  });
  it('bounds zoom and handles cancelled pointer gestures', async () => {
    setup(async () => Response.json(graph));
    const canvas = await screen.findByRole('group', { name: 'GitHub knowledge graph' });
    for (let index = 0; index < 15; index++) fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(canvas.style.transform).toContain('scale(0.5)');
    expect(screen.getByRole('button', { name: 'Zoom out' })).toHaveProperty('disabled', true);
    for (let index = 0; index < 15; index++) fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(canvas.style.transform).toContain('scale(2.5)');
    expect(screen.getByRole('button', { name: 'Zoom in' })).toHaveProperty('disabled', true);
    const viewport = canvas.parentElement!;
    fireEvent.pointerDown(viewport, { pointerId: 1, button: 0, clientX: 0, clientY: 0 });
    fireEvent.pointerCancel(viewport, { pointerId: 1 });
    const transform = canvas.style.transform;
    fireEvent.pointerMove(viewport, { pointerId: 1, clientX: 100, clientY: 100 });
    expect(canvas.style.transform).toBe(transform);
    fireEvent.pointerDown(viewport, { pointerId: 2, button: 2, clientX: 0, clientY: 0 });
    fireEvent.pointerMove(viewport, { pointerId: 2, clientX: 100, clientY: 100 });
    expect(canvas.style.transform).toBe(transform);
    const node = within(canvas).getByRole('button', { name: 'Add Redis caching, Commit' });
    fireEvent.pointerDown(node, { pointerId: 3, button: 0, clientX: 0, clientY: 0 });
    fireEvent.pointerCancel(viewport, { pointerId: 3 });
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }), { detail: 1 });
    expect(canvas.style.transform).toContain('scale(2.3)');
  });
  it('shows a clean offline message and retries without using demo data', async () => {
    let unavailable = true;
    setup(async () => unavailable ? Response.json({ detail: 'Knowledge graph is unavailable. Check the local Neo4j service and try again.' }, { status: 503 }) : Response.json(graph));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Knowledge graph is unavailable. Check the local Neo4j service and try again.');
    expect(screen.queryByRole('group', { name: 'GitHub knowledge graph' })).toBeNull();
    unavailable = false;
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByRole('group', { name: 'GitHub knowledge graph' });
  });
  it('shows the empty response clearly', async () => {
    setup(async () => Response.json({ nodes: [], edges: [] }));
    await screen.findByText('No GitHub graph data is available for your connected repositories.');
    expect(screen.queryByText('Sample data')).toBeNull();
  });
  it('shows access denied rather than a fake graph', async () => {
    setup(async () => Response.json({}, { status: 403 }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Your account does not have access to this resource.');
  });
});
