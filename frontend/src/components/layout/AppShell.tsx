import type { ReactNode } from 'react';
import { AppSidebar } from './AppSidebar';

export function AppShell({ children, rightPanel, className = '' }: { children: ReactNode; rightPanel?: ReactNode; className?: string }) {
  return <div className={`app-shell ${rightPanel ? '' : 'no-right-panel'}`}>
    <a href="#main-content" className="skip-link">Skip to content</a>
    <AppSidebar />
    <main id="main-content" className={`main-content ${className}`}>{children}</main>
    {rightPanel}
  </div>;
}
