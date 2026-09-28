import { useEffect, useRef, useState } from 'react';
import { greeting } from '../components/chat/greeting';
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
  const [hour] = useState(() => new Date().getHours());
  const [leaving, setLeaving] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const submit = (question: string) => {
    if (leaving) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { startChat(question); return; }
    setLeaving(true);
    timer.current = setTimeout(() => startChat(question), 140);
  };
  return <AppShell className="home-page" rightPanel={<RightPanel label="Your connected knowledge"><ConnectedSources /><SuggestedQuestions onSelect={submit} /><PanelCard><h2 className="card-heading">Knowledge context</h2><p className="state-message">Answers use your available indexed sources and related knowledge. Source details appear with each response.</p></PanelCard></RightPanel>}>
    <div key={location.key} className={`welcome-area ${leaving ? 'is-leaving' : ''}`}><div className="welcome-heading"><BrandMark /><h1>{greeting(profile?.full_name, hour)}</h1></div><ChatInput key={location.key} disabled={loading || leaving} onSubmit={submit} /><p className="demo-caption">{profile ? 'Ask your connected knowledge' : 'Sign in to ask a question'} · Conversations stay in this browser tab</p></div>
  </AppShell>;
}
