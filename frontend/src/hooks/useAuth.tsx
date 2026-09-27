import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { api, ApiError, SESSION_EXPIRED_EVENT, type UserProfile } from '../services/api';

const storageKey = 'ekos.session-token';
function readToken() { try { return sessionStorage.getItem(storageKey); } catch { return null; } }
function persistToken(token: string | null) {
  try { if (token) sessionStorage.setItem(storageKey, token); else sessionStorage.removeItem(storageKey); } catch { /* Memory-only session when storage is unavailable. */ }
}
interface AuthContextValue {
  token: string | null; profile: UserProfile | null; loading: boolean; error: string;
  signIn: (email: string, password: string) => Promise<void>; signOut: () => void;
}
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken);
  const tokenRef = useRef(token);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(!!token);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const clearSession = useCallback(() => {
    generation.current += 1; tokenRef.current = null; persistToken(null);
    setToken(null); setProfile(null); setLoading(false);
  }, []);

  useEffect(() => {
    const currentToken = tokenRef.current;
    if (!currentToken) return;
    const controller = new AbortController();
    const version = generation.current;
    api.getProfile(currentToken, controller.signal).then(user => {
      if (!controller.signal.aborted && version === generation.current) { setProfile(user); setError(''); }
    }).catch(reason => {
      if (controller.signal.aborted || version !== generation.current) return;
      if (reason instanceof ApiError && (reason.status === 401 || reason.status === 403)) clearSession();
      setError(reason instanceof Error ? reason.message : 'Unable to load your profile.');
    }).finally(() => { if (!controller.signal.aborted && version === generation.current) setLoading(false); });
    return () => controller.abort();
  }, [clearSession]);

  useEffect(() => {
    const expire = (event: Event) => {
      if ((event as CustomEvent<string>).detail !== tokenRef.current) return;
      clearSession(); setError('Your session has expired. Please sign in again.');
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
  }, [clearSession]);

  const signIn = async (email: string, password: string) => {
    const version = ++generation.current;
    const response = await api.login(email, password);
    const user = await api.getProfile(response.access_token);
    if (version !== generation.current) return;
    tokenRef.current = response.access_token; persistToken(response.access_token);
    setToken(response.access_token); setProfile(user); setLoading(false); setError('');
  };
  const signOut = () => {
    clearSession(); setError('');
    // JWT logout is client-side even if the optional server acknowledgement fails.
    void api.logout().catch(() => {});
  };
  return <AuthContext.Provider value={{ token, profile, loading, error, signIn, signOut }}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth requires AuthProvider');
  return context;
}
