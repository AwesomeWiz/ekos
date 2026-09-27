import { Archive, Database, FileText, Github, SquareCode, User } from 'lucide-react';
import type { EntityType } from '../data/demoData';

export function EntityIcon({ type, size = 18 }: { type: EntityType; size?: number }) {
  const Icon = { Service: Archive, Technology: Database, Person: User, 'Jira Issue': SquareCode, Document: FileText, 'GitHub Repository': Github }[type];
  return <Icon size={size} strokeWidth={1.65} aria-hidden="true" />;
}
