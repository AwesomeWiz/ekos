export function greeting(name: string | undefined, hour: number) {
  const firstName = name?.trim().split(/\s+/)[0] || 'there';
  const period = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
  return `Good ${period}, ${firstName}.`;
}
