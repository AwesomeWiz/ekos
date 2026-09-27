import { Route, Routes } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { ChatPage } from './pages/ChatPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { ConnectorsPage } from './pages/ConnectorsPage';
import { AppShell } from './components/layout/AppShell';
import { Link } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { AccountPage } from './pages/AccountPage';
import { AuthProvider } from './hooks/useAuth';
import { ChatProvider } from './hooks/useChat';
import { ConnectorsProvider } from './hooks/useConnectors';

export function App() {
  return <AuthProvider><ConnectorsProvider><ChatProvider><Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/chat" element={<HomePage />} />
    <Route path="/chat/:conversationId" element={<ChatPage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/account" element={<AccountPage />} />
    <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
    <Route path="/connectors" element={<ConnectorsPage />} />
    <Route path="*" element={<AppShell><div className="empty-page"><h1>Page not found</h1><Link className="text-link" to="/">Start a new chat →</Link></div></AppShell>} />
  </Routes></ChatProvider></ConnectorsProvider></AuthProvider>;
}
