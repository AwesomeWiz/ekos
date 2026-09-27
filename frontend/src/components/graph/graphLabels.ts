import type { GraphNodeData } from '../../services/api';

export function graphNodeLabel(node: GraphNodeData): string {
  return node.type === 'Commit' && node.description.trim()
    ? node.description.trim().split(/\r?\n/)[0]
    : node.name;
}
