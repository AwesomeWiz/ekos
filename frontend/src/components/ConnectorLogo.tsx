import { Github, Puzzle } from 'lucide-react';

/** Small local vector marks; no remote assets or icon package required. */
export function ConnectorLogo({ type }: { type: string }) {
  const kind = type.trim().toLowerCase();
  if (kind === 'github') return <Github size={24} aria-hidden="true" />;
  if (kind === 'jira') return <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#2684FF" d="M12 1 23 12 12 23 1 12Z" /><path fill="#0052CC" d="m12 1 5.5 5.5L12 12 6.5 6.5Z" /><path fill="white" d="m12 7 5 5-5 5-5-5Z" /></svg>;
  if (kind === 'confluence') return <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#2684FF" d="M2 16c5-8 9 3 16-4l4 6c-8 10-13-3-17 4Z" /><path fill="#0052CC" d="M22 8C17 16 13 5 6 12L2 6C10-4 15 9 19 2Z" /></svg>;
  if (kind === 'slack') return <svg viewBox="0 0 24 24" aria-hidden="true"><g fill="#36C5F0"><rect x="2" y="8" width="9" height="4" rx="2"/><circle cx="9" cy="4" r="2"/></g><g fill="#2EB67D"><rect x="12" y="2" width="4" height="9" rx="2"/><circle cx="20" cy="9" r="2"/></g><g fill="#ECB22E"><rect x="13" y="12" width="9" height="4" rx="2"/><circle cx="15" cy="20" r="2"/></g><g fill="#E01E5A"><rect x="8" y="13" width="4" height="9" rx="2"/><circle cx="4" cy="15" r="2"/></g></svg>;
  return <Puzzle size={24} aria-hidden="true" />;
}
