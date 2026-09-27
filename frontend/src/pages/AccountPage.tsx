import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';

export function AccountPage() {
  const { profile, loading } = useAuth();
  return <AppShell><section className="account-page"><h1>Account</h1>
    {loading ? <p className="state-message" role="status">Loading profile…</p>
      : !profile ? <p className="state-message">Sign in to view your account. <Link className="text-link" to="/login">Sign in →</Link></p>
      : <div className="panel-card account-card"><dl>
        <div><dt>Name</dt><dd>{profile.full_name}</dd></div>
        <div><dt>Email</dt><dd>{profile.email}</dd></div>
        <div><dt>Role</dt><dd><span className="role-badge">{profile.role}</span></dd></div>
        <div><dt>Organization</dt><dd>{profile.organization || 'Not assigned'}</dd></div>
      </dl><h2>Permissions</h2>{profile.permissions.length ? <ul>{profile.permissions.map(permission => <li key={`${permission.resource}:${permission.action}`}>{permission.resource}: {permission.action}</li>)}</ul> : <p className="state-message">No permissions assigned.</p>}</div>}
  </section></AppShell>;
}
