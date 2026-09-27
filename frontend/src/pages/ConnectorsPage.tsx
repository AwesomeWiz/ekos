import { AppShell } from '../components/layout/AppShell';
import { ConnectedSources } from '../components/chat/ConnectedSources';

export function ConnectorsPage() {
  return <AppShell><div className="connectors-page"><h1>Connectors</h1><p className="text-muted mt-3 mb-8">Your team's registered sources and latest recorded status.</p><ConnectedSources full /></div></AppShell>;
}
