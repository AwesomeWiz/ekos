import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';

export function LoginPage() {
  const { signIn, profile, error: sessionError } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  return <AppShell><div className="login-page"><h1>Sign in to EKOS</h1><p className="text-muted">Access your organization's connected sources.</p>
    {profile ? <Link className="primary-button" to="/connectors">View connected sources</Link> : <form className="login-form" onSubmit={async event => {
      event.preventDefault(); if (pending) return; setPending(true); setError('');
      try { await signIn(email.trim(), password); setPassword(''); navigate('/connectors', { replace: true }); }
      catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to sign in.'); }
      finally { setPending(false); }
    }}>
      <label>Email<input type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} required disabled={pending} /></label>
      <label>Password<input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required disabled={pending} /></label>
      {(error || sessionError) && <p className="inline-error" role="alert">{error || sessionError}</p>}
      <button className="primary-button" type="submit" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</button>
    </form>}
    <Link className="text-link" to="/">Continue with the sample workspace</Link>
  </div></AppShell>;
}
