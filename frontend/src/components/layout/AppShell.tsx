import { useState, type ReactNode } from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { AppSidebar } from './AppSidebar';

function usePanelState(key: string, narrow: boolean) {
  const [collapsed, setCollapsed] = useState(() => {
    try { const saved = sessionStorage.getItem(key); return saved === null ? narrow : saved === 'true'; } catch { return narrow; }
  });
  return [collapsed, () => setCollapsed(value => {
    try { sessionStorage.setItem(key, String(!value)); } catch { /* Keep controls usable without storage. */ }
    return !value;
  })] as const;
}

export function AppShell({ children, rightPanel, className = '' }: { children: ReactNode; rightPanel?: ReactNode; className?: string }) {
  const [leftClosed, toggleLeft] = usePanelState('ekos.ui.left-collapsed', window.innerWidth < 1000);
  const [rightClosed, toggleRight] = usePanelState('ekos.ui.right-collapsed', window.innerWidth < 1200);
  return <div className={`app-shell ${rightPanel ? '' : 'no-right-panel'} ${leftClosed ? 'left-collapsed' : ''} ${rightPanel && rightClosed ? 'right-collapsed' : ''}`}>
    <a href="#main-content" className="skip-link">Skip to content</a>
    <AppSidebar collapsed={leftClosed} onToggle={toggleLeft} />
    <main id="main-content" className={`main-content ${className}`}>{children}</main>
    {rightPanel && <div className="right-panel-slot">
      <button className="icon-button panel-toggle right-toggle" aria-label={rightClosed ? 'Expand knowledge panel' : 'Collapse knowledge panel'} title={rightClosed ? 'Expand knowledge panel' : 'Collapse knowledge panel'} aria-expanded={!rightClosed} aria-controls="knowledge-panel-content" onClick={toggleRight}>{rightClosed ? <PanelRightOpen size={19} /> : <PanelRightClose size={19} />}</button>
      <div id="knowledge-panel-content" hidden={rightClosed}>{rightPanel}</div>
    </div>}
  </div>;
}
