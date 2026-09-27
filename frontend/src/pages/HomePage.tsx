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
  const { profile } = useAuth();
  const { startChat } = useChat();
  const location = useLocation();
  return <AppShell className="home-page" rightPanel={<RightPanel label="Your connected knowledge"><ConnectedSources /><SuggestedQuestions /><PanelCard><h2 className="card-heading">Sample workspace</h2><p className="state-message">Chat answers and the knowledge graph use sample knowledge. Source status comes from your connected account.</p></PanelCard></RightPanel>}>
    <div className="welcome-area"><div className="welcome-heading"><BrandMark /><h1>{profile ? `Hello, ${profile.full_name.split(' ')[0]}.` : 'Hello, there.'}</h1></div><ChatInput key={location.key} onSubmit={startChat} /><p className="demo-caption">Explore sample knowledge · Conversations stay in this browser tab</p></div>
  </AppShell>;
}
