import { Archive, Database, FileText, Github, GitCommitHorizontal, SquareCode, User } from 'lucide-react';

export function EntityIcon({ type, size = 18 }: { type: string; size?: number }) {
  const icons: Record<string, typeof Archive> = { Service: Archive, Technology: Database, Person: User, Commit: GitCommitHorizontal, 'Jira Issue': SquareCode, Document: FileText, 'GitHub Repository': Github };
  const Icon = icons[type] || FileText;
  return <Icon size={size} strokeWidth={1.65} aria-hidden="true" />;
}
