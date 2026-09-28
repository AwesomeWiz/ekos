// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { RightPanel } from './components/layout/RightPanel';
import { WaitingStatus } from './components/chat/WaitingStatus';
import { greeting } from './components/chat/greeting';

vi.mock('./hooks/useAuth', () => ({ useAuth: () => ({ profile: { full_name: 'Test Developer', role: 'Developer' }, loading: false, signOut: vi.fn() }) }));
vi.mock('./hooks/useChat', () => ({ useChat: () => ({ conversations: [{ id: 'one', title: 'Saved question' }] }) }));
beforeEach(() => { sessionStorage.clear(); vi.stubGlobal('innerWidth', 1366); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });
function shell() {
  return render(<MemoryRouter><AppShell rightPanel={<RightPanel label="Knowledge">Panel contents</RightPanel>}><h1>Workspace</h1></AppShell></MemoryRouter>);
}
describe('UI polish interactions', () => {
  it('collapses panels independently, keeps navigation accessible, and remembers preferences', () => {
    const view = shell();
    fireEvent.click(screen.getByRole('button', { name: 'Collapse navigation' }));
    expect(screen.getByRole('link', { name: 'Knowledge graph' }).getAttribute('title')).toBe('Knowledge graph');
    expect(screen.queryByRole('link', { name: 'Saved question' })).toBeNull();
    expect(screen.getByRole('complementary', { name: 'Knowledge' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Collapse knowledge panel' }));
    expect(screen.queryByRole('complementary', { name: 'Knowledge' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Expand knowledge panel' }).getAttribute('aria-expanded')).toBe('false');
    view.unmount(); shell();
    fireEvent.click(screen.getByRole('button', { name: 'Expand knowledge panel' }));
    expect(screen.getByRole('complementary', { name: 'Knowledge' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Expand navigation' }));
    expect(screen.getByRole('link', { name: 'Saved question' })).toBeTruthy();
  });
  it.each([1366, 1920])('starts expanded at desktop width %s', width => {
    vi.stubGlobal('innerWidth', width); shell();
    expect(screen.getByRole('button', { name: 'Collapse navigation' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Collapse knowledge panel' })).toBeTruthy();
  });
  it('starts with narrow rails on a narrow desktop while preserving expand controls', () => {
    vi.stubGlobal('innerWidth', 900); shell();
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Expand knowledge panel' })).toBeTruthy();
  });
  it.each([[9, 'morning'], [12, 'afternoon'], [18, 'evening']])('chooses a stable greeting at hour %s', (hour, period) => {
    expect(greeting('  Taylor Smith', Number(hour))).toBe(`Good ${period}, Taylor.`);
    expect(greeting(undefined, Number(hour))).toBe(`Good ${period}, there.`);
  });
  it('rotates one waiting area and stops its timer on unmount', () => {
    vi.useFakeTimers(); const view = render(<WaitingStatus />);
    expect(screen.getAllByRole('status')).toHaveLength(1);
    act(() => vi.advanceTimersByTime(3200));
    expect(screen.getByText(/Working on your answer/)).toBeTruthy();
    view.unmount(); expect(vi.getTimerCount()).toBe(0);
  });
  it('keeps waiting copy static with reduced motion', () => {
    vi.useFakeTimers();
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    render(<WaitingStatus />); act(() => vi.advanceTimersByTime(10000));
    expect(screen.getByText(/Thinking it through/)).toBeTruthy();
    expect(vi.getTimerCount()).toBe(0);
  });
});
