import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { demoAnswer, demoQuestion, entities, type EntityId } from '../data/demoData';
import { useAuth } from './useAuth';
import { api, type SearchResult } from '../services/api';

export interface ChatTurn {
  id: string; question: string; answer: string | null; sourceIds: EntityId[]; relatedIds: EntityId[];
  mode?: 'sample' | 'retrieval' | 'empty-index' | 'no-results' | 'error' | 'sign-in'; results?: SearchResult[];
}
export interface Conversation { id: string; title: string; turns: ChatTurn[]; example?: boolean }
interface ChatContextValue { conversations: Conversation[]; startChat: (question: string) => void; sendFollowUp: (id: string, question: string) => void }
const ChatContext = createContext<ChatContextValue | null>(null);
function seedConversation(): Conversation {
  return { id: 'redis', title: 'Why was redis introduced?', example: true, turns: [{ id: 'redis-example', question: demoQuestion, answer: demoAnswer.join('\n\n'), sourceIds: ['issue', 'document', 'repository'], relatedIds: ['payment', 'redis', 'issue'] }] };
}
function isTurn(value: unknown): value is ChatTurn {
  if (!value || typeof value !== 'object') return false;
  const turn = value as ChatTurn;
  return typeof turn.id === 'string' && typeof turn.question === 'string' && (typeof turn.answer === 'string' || turn.answer === null)
    && [turn.sourceIds, turn.relatedIds].every(ids => Array.isArray(ids) && ids.every(id => typeof id === 'string' && Object.hasOwn(entities, id)))
    && (turn.mode === undefined || ['sample', 'retrieval', 'empty-index', 'no-results', 'error', 'sign-in'].includes(turn.mode))
    && (turn.results === undefined || (Array.isArray(turn.results) && turn.results.every(result => typeof result.document_id === 'string' && typeof result.text === 'string' && typeof result.distance === 'number' && result.metadata && typeof result.metadata === 'object')));
}
function readConversations(key: string): Conversation[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (Array.isArray(value) && value.every(item => item && typeof item.id === 'string' && typeof item.title === 'string' && Array.isArray(item.turns) && item.turns.every(isTurn))) {
      return value.slice(0, 50).map(chat => ({ ...chat, turns: chat.turns.map((turn: ChatTurn) => ({ ...turn, mode: turn.mode || 'sample' })) }));
    }
  } catch { /* Corrupt or unavailable browser storage must not break the demo. */ }
  return [seedConversation()];
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
        finish({ mode: 'sign-in', answer: 'Sign in to search your indexed knowledge.', results: [] });
        requests.current.delete(turn.id);
        continue;
      }
      void api.semanticSearch(token, turn.question, 5, controller.signal).then(response => {
        if (response.document_count === 0) finish({ mode: 'empty-index', answer: 'No indexed knowledge is available yet. Sync the GitHub connector first.', results: [] });
        else if (!response.results.length) finish({ mode: 'no-results', answer: 'No indexed knowledge matched this query.', results: [] });
        else finish({ mode: 'retrieval', answer: 'EKOS found the following relevant knowledge:', results: response.results });
      }).catch(reason => {
        finish({ mode: 'error', answer: reason instanceof Error ? reason.message : 'Knowledge search could not be completed.', results: [] });
      }).finally(() => { if (requests.current.get(turn.id) === controller) requests.current.delete(turn.id); });
    }
  }, [conversations, token]);
  const pendingTurn = (question: string): ChatTurn => ({ id: crypto.randomUUID(), question, answer: null, sourceIds: [], relatedIds: [], mode: 'retrieval', results: [] });
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
