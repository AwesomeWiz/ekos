import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './useAuth';
import { api, type ChatSource, type GraphRelationship } from '../services/api';

export interface ChatTurn {
  id: string; question: string; answer: string | null;
  mode: 'chat' | 'error' | 'sign-in'; sources: ChatSource[]; graphContext: GraphRelationship[];
}
export interface Conversation { id: string; title: string; turns: ChatTurn[]; example?: boolean }
interface ChatContextValue { conversations: Conversation[]; startChat: (question: string) => void; sendFollowUp: (id: string, question: string) => void }
const ChatContext = createContext<ChatContextValue | null>(null);
function isTurn(value: unknown): value is ChatTurn {
  if (!value || typeof value !== 'object') return false;
  const turn = value as ChatTurn;
  return typeof turn.id === 'string' && typeof turn.question === 'string' && (typeof turn.answer === 'string' || turn.answer === null)
    && ['chat', 'error', 'sign-in'].includes(turn.mode)
    && Array.isArray(turn.sources) && turn.sources.every(source => source && typeof source.snippet === 'string')
    && Array.isArray(turn.graphContext) && turn.graphContext.every(edge => edge && [edge.source, edge.relationship, edge.target].every(value => typeof value === 'string'));
}
function readConversations(key: string): Conversation[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (Array.isArray(value)) return value.filter(item => item && !item.example && typeof item.id === 'string' && typeof item.title === 'string' && Array.isArray(item.turns) && item.turns.every(isTurn)).slice(0, 50);
  } catch { /* Unavailable or old sample history must not break chat. */ }
  return [];
}

function SessionChats({ children, storageKey }: { children: ReactNode; storageKey: string }) {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [conversations, setConversations] = useState(() => readConversations(storageKey));
  const requests = useRef(new Map<string, AbortController>());
  useEffect(() => {
    try { sessionStorage.setItem(storageKey, JSON.stringify(conversations)); } catch { /* React history remains usable. */ }
  }, [conversations, storageKey]);
  useEffect(() => {
    const active = requests.current;
    return () => { active.forEach(controller => controller.abort()); active.clear(); };
  }, [token]);
  useEffect(() => {
    for (const chat of conversations) for (const turn of chat.turns) {
      if (turn.answer !== null || requests.current.has(turn.id)) continue;
      const controller = new AbortController();
      requests.current.set(turn.id, controller);
      const finish = (update: Partial<ChatTurn>) => {
        if (!controller.signal.aborted) setConversations(chats => chats.map(item => ({ ...item, turns: item.turns.map(value => value.id === turn.id ? { ...value, ...update } : value) })));
      };
      if (!token) {
        finish({ mode: 'sign-in', answer: 'Sign in to chat with your indexed knowledge.', sources: [], graphContext: [] });
        requests.current.delete(turn.id);
        continue;
      }
      void api.chat(token, turn.question, controller.signal).then(response => {
        finish({ mode: 'chat', answer: response.answer, sources: response.sources, graphContext: response.graph_context || [] });
      }).catch(reason => {
        finish({ mode: 'error', answer: reason instanceof Error ? reason.message : 'Chat could not be completed.', sources: [], graphContext: [] });
      }).finally(() => { if (requests.current.get(turn.id) === controller) requests.current.delete(turn.id); });
    }
  }, [conversations, token]);
  const pendingTurn = (question: string): ChatTurn => ({ id: crypto.randomUUID(), question, answer: null, mode: 'chat', sources: [], graphContext: [] });
  const startChat = (question: string) => {
    if (!question.trim()) return;
    const id = crypto.randomUUID();
    setConversations(chats => [{ id, title: question.trim(), turns: [pendingTurn(question.trim())] }, ...chats].slice(0, 50));
    navigate(`/chat/${id}`);
  };
  const sendFollowUp = (id: string, question: string) => {
    if (!question.trim()) return;
    setConversations(chats => chats.map(chat => chat.id !== id || chat.turns.some(turn => turn.answer === null) ? chat : { ...chat, turns: [...chat.turns, pendingTurn(question.trim())] }));
  };
  return <ChatContext.Provider value={{ conversations, startChat, sendFollowUp }}>{children}</ChatContext.Provider>;
}
export function ChatProvider({ children }: { children: ReactNode }) {
  const { profile, loading } = useAuth();
  const key = `ekos.chats.${loading ? 'restoring' : profile?.id || 'guest'}`;
  return <SessionChats key={key} storageKey={key}>{children}</SessionChats>;
}
export function useChat() {
  const context = useContext(ChatContext);
  if (!context) throw new Error('useChat requires ChatProvider');
  return context;
}
