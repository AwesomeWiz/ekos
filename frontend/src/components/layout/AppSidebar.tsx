import { LogOut, Plus, Puzzle, Share2, UserCircle } from 'lucide-react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Brand } from '../Brand';
import { useAuth } from '../../hooks/useAuth';
import { useChat } from '../../hooks/useChat';

export function AppSidebar() {
  const { pathname } = useLocation();
  const { profile, loading, signOut } = useAuth();
  const { conversations } = useChat();
  const initials = profile?.full_name.split(' ').map(part => part[0]).slice(0, 2).join('') || 'EK';
  return <aside className="app-sidebar">
    <Link to="/" className="brand-link" aria-label="EKOS home"><Brand /></Link>
    <nav aria-label="Main navigation" className="main-nav">
      <Link to="/" className={`nav-item ${pathname === '/' || pathname === '/chat' ? 'active' : ''}`} aria-current={pathname === '/' || pathname === '/chat' ? 'page' : undefined}><Plus size={19} />New chat</Link>
      <NavLink to="/knowledge-graph" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Share2 size={19} />Knowledge graph</NavLink>
      <NavLink to="/connectors" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Puzzle size={19} />Connectors</NavLink>
      {profile && <NavLink to="/account" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><UserCircle size={19} />Account</NavLink>}
    </nav>
    <section className="chat-history" aria-label="Chat history">
      <h2>Chats</h2>
      {conversations.map(chat => <NavLink key={chat.id} to={`/chat/${chat.id}`} title={chat.title} className={({ isActive }) => `history-item ${isActive ? 'active' : ''}`}><span>{chat.title}</span>{chat.example && <small>Example</small>}</NavLink>)}
    </section>
    <div className="user-profile">
      <span className="avatar">{initials}</span>
      <div className="min-w-0 flex-1"><p className="user-name">{profile?.full_name || 'Sample workspace'}</p><p className="text-xs text-muted mt-1">{loading ? 'Restoring session…' : profile?.role ? <span className="role-badge">{profile.role}</span> : <Link to="/login" className="text-link">Sign in</Link>}</p></div>
      {profile && <button className="icon-button" aria-label="Sign out" title="Sign out" onClick={signOut}><LogOut size={18} /></button>}
    </div>
  </aside>;
}
