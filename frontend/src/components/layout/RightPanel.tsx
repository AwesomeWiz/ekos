import type { ReactNode } from 'react';

export function RightPanel({ children, label }: { children: ReactNode; label: string }) {
  return <aside className="right-panel" aria-label={label}>{children}</aside>;
}
export function PanelCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel-card ${className}`}>{children}</section>;
}
