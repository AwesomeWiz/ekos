import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { api, type ManagedUser, type NewUser, type UserRole } from '../services/api';

export function UsersPage() {
  const { profile, token, loading, error } = useAuth();
  return <AppShell><section className="account-page users-page"><h1>User Management</h1>
    {loading ? <p className="state-message" role="status">Loading profile…</p>
      : !profile || !token ? <><p className="state-message">{error || 'Sign in to manage users.'}</p><Link className="text-link" to="/login">Sign in</Link></>
      : profile.role !== 'Administrator' ? <p className="inline-error" role="alert">Administrator access required.</p>
      : <UserManagement key={token} token={token} currentUserId={profile.id} />}
  </section></AppShell>;
}

function UserManagement({ token, currentUserId }: { token: string; currentUserId: string }) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roles, setRoles] = useState<UserRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [revision, setRevision] = useState(0);
  const [form, setForm] = useState<NewUser>({ full_name: '', email: '', password: '', role_id: '' });
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    setLoading(true); setError('');
    void Promise.all([api.getUsers(token, controller.signal), api.getUserRoles(token, controller.signal)]).then(([people, available]) => {
      if (controller.signal.aborted) return;
      setUsers(people); setRoles(available);
      setForm(value => ({ ...value, role_id: value.role_id || available.find(role => role.role_name === 'Developer')?.id || available[0]?.id || '' }));
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to load users.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, revision]);

  const update = async (user: ManagedUser, change: { role_id?: string; status?: boolean }) => {
    if (pending) return;
    const signal = active.current?.signal;
    setPending(true); setError(''); setNotice('');
    try {
      const saved = await api.updateUser(token, user.id, change, signal);
      if (!signal?.aborted) { setUsers(values => values.map(value => value.id === saved.id ? saved : value)); setNotice('User updated.'); }
    } catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Unable to update user.'); }
    finally { if (!signal?.aborted) setPending(false); }
  };

  if (loading) return <p className="state-message" role="status">Loading users…</p>;
  return <>
    {error && <p className="inline-error" role="alert">{error}</p>}
    {notice && <p className="state-message" role="status">{notice}</p>}
    {!roles.length ? <button className="text-link" onClick={() => setRevision(value => value + 1)}>Try again</button> : <>
      <div className="panel-card account-card"><h2>Add User</h2><form className="login-form" onSubmit={async event => {
        event.preventDefault(); if (pending) return;
        const signal = active.current?.signal;
        setPending(true); setError(''); setNotice('');
        try {
          const user = await api.createUser(token, { ...form, full_name: form.full_name.trim(), email: form.email.trim() }, signal);
          if (!signal?.aborted) { setUsers(values => [...values, user]); setForm(value => ({ ...value, full_name: '', email: '', password: '' })); setNotice('User created.'); }
        } catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Unable to create user.'); }
        finally { if (!signal?.aborted) setPending(false); }
      }}>
        <label>Full name<input required maxLength={255} value={form.full_name} disabled={pending} onChange={event => setForm(value => ({ ...value, full_name: event.target.value }))} /></label>
        <label>Email<input type="email" required autoComplete="off" value={form.email} disabled={pending} onChange={event => setForm(value => ({ ...value, email: event.target.value }))} /></label>
        <label>Initial password<input type="password" required minLength={8} maxLength={72} autoComplete="new-password" value={form.password} disabled={pending} onChange={event => setForm(value => ({ ...value, password: event.target.value }))} /></label>
        <label>Role<select value={form.role_id} required disabled={pending} onChange={event => setForm(value => ({ ...value, role_id: event.target.value }))}>{roles.map(role => <option key={role.id} value={role.id}>{role.role_name}</option>)}</select></label>
        <button className="primary-button" disabled={pending} type="submit">{pending ? 'Saving…' : 'Add User'}</button>
      </form></div>
      <h2>Users</h2>
      {users.map(user => <article className="panel-card account-card" key={user.id} aria-label={user.full_name}>
        <h3>{user.full_name}</h3><p className="item-meta">{user.email}</p>
        <div className="login-form"><label>Role for {user.full_name}<select value={user.role_id || ''} disabled={pending || user.id === currentUserId} onChange={event => void update(user, { role_id: event.target.value })}>
          {!user.role_id && <option value="" disabled>Not assigned</option>}{roles.map(role => <option key={role.id} value={role.id}>{role.role_name}</option>)}
        </select></label></div>
        <p className="item-meta">{user.status ? 'Enabled' : 'Disabled'}</p>
        <button className="text-link" disabled={pending || user.id === currentUserId} onClick={() => void update(user, { status: !user.status })}>{user.status ? 'Disable' : 'Enable'}</button>
      </article>)}
    </>}
  </>;
}
