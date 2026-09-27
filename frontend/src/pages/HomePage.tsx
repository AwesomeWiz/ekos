import { useLocation } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { PanelCard, RightPanel } from '../components/layout/RightPanel';
import { ConnectedSources } from '../components/chat/ConnectedSources';
import { SuggestedQuestions } from '../components/chat/SuggestedQuestions';
import { ChatInput } from '../components/chat/ChatInput';
import { BrandMark } from '../components/Brand';
import { useAuth } from '../hooks/useAuth';
import { useChat } from '../hooks/useChat';

export function HomePage() {
  const { profile, loading } = useAuth();
  const { startChat } = useChat();
  const location = useLocation();
  return <AppShell className="home-page" rightPanel={<RightPanel label="Your connected knowledge"><ConnectedSources /><SuggestedQuestions /><PanelCard><h2 className="card-heading">Knowledge search</h2><p className="state-message">Search retrieves indexed GitHub knowledge. It does not generate AI answers. The knowledge graph remains sample data.</p></PanelCard></RightPanel>}>
    <div className="welcome-area"><div className="welcome-heading"><BrandMark /><h1>{profile ? `Hello, ${profile.full_name.split(' ')[0]}.` : 'Hello, there.'}</h1></div><ChatInput key={location.key} disabled={loading} onSubmit={startChat} /><p className="demo-caption">{profile ? 'Semantic search' : 'Sign in for semantic search'} · Conversations stay in this browser tab</p></div>
  </AppShell>;
}
