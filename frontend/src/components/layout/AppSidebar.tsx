import { LogOut, PanelLeftClose, PanelLeftOpen, Plus, Puzzle, Share2, UserCircle } from 'lucide-react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Brand } from '../Brand';
import { useAuth } from '../../hooks/useAuth';
import { useChat } from '../../hooks/useChat';

export function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { pathname } = useLocation();
  const { profile, loading, signOut } = useAuth();
  const { conversations } = useChat();
  const initials = profile?.full_name.split(' ').map(part => part[0]).slice(0, 2).join('') || 'EK';
  return <aside className="app-sidebar">
    <button className="icon-button panel-toggle left-toggle" aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'} title={collapsed ? 'Expand navigation' : 'Collapse navigation'} aria-expanded={!collapsed} onClick={onToggle}>{collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}</button>
    <Link to="/" title="EKOS home" className="brand-link" aria-label="EKOS home"><Brand /></Link>
    <nav aria-label="Main navigation" className="main-nav">
      <Link to="/" aria-label="New chat" title="New chat" className={`nav-item ${pathname === '/' || pathname === '/chat' ? 'active' : ''}`} aria-current={pathname === '/' || pathname === '/chat' ? 'page' : undefined}><Plus size={19} /><span className="nav-label">New chat</span></Link>
      <NavLink to="/knowledge-graph" aria-label="Knowledge graph" title="Knowledge graph" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Share2 size={19} /><span className="nav-label">Knowledge graph</span></NavLink>
      <NavLink to="/connectors" aria-label="Connectors" title="Connectors" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Puzzle size={19} /><span className="nav-label">Connectors</span></NavLink>
      {profile && <NavLink to="/account" aria-label="Account" title="Account" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><UserCircle size={19} /><span className="nav-label">Account</span></NavLink>}
      {profile?.role === 'Administrator' && <NavLink to="/admin/users" aria-label="User Management" title="User Management" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><UserCircle size={19} /><span className="nav-label">User Management</span></NavLink>}
    </nav>
    <section hidden={collapsed} className="chat-history" aria-label="Chat history">
      <h2>Chats</h2>
      {conversations.map(chat => <NavLink key={chat.id} to={`/chat/${chat.id}`} title={chat.title} className={({ isActive }) => `history-item ${isActive ? 'active' : ''}`}><span>{chat.title}</span>{chat.example && <small>Example</small>}</NavLink>)}
    </section>
    <div className="user-profile">
      <span className="avatar">{initials}</span>
      <div hidden={collapsed} className="min-w-0 flex-1"><p className="user-name">{profile?.full_name || 'Sample workspace'}</p><p className="text-xs text-muted mt-1">{loading ? 'Restoring session…' : profile?.role ? <span className="role-badge">{profile.role}</span> : <Link to="/login" className="text-link">Sign in</Link>}</p></div>
      {profile && <button className="icon-button" aria-label="Sign out" title="Sign out" onClick={signOut}><LogOut size={18} /></button>}
    </div>
  </aside>;
}
