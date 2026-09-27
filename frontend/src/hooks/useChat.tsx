import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { demoAnswer, demoQuestion, entities, getDemoReply, type EntityId } from '../data/demoData';
import { useAuth } from './useAuth';

export interface ChatTurn { id: string; question: string; answer: string | null; sourceIds: EntityId[]; relatedIds: EntityId[] }
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
    && [turn.sourceIds, turn.relatedIds].every(ids => Array.isArray(ids) && ids.every(id => typeof id === 'string' && Object.hasOwn(entities, id)));
}
function readConversations(key: string): Conversation[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (Array.isArray(value) && value.every(item => item && typeof item.id === 'string' && typeof item.title === 'string' && Array.isArray(item.turns) && item.turns.every(isTurn))) return value.slice(0, 50);
  } catch { /* Corrupt or unavailable browser storage must not break the demo. */ }
  return [seedConversation()];
}

function SessionChats({ children, storageKey }: { children: ReactNode; storageKey: string }) {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState(() => readConversations(storageKey));
  useEffect(() => {
    try { sessionStorage.setItem(storageKey, JSON.stringify(conversations)); } catch { /* React history remains usable. */ }
  }, [conversations, storageKey]);
  useEffect(() => {
    if (!conversations.some(chat => chat.turns.some(turn => turn.answer === null))) return;
    // Yield once so the submitted question renders; this is a local fixture, not an AI call.
    const timer = setTimeout(() => setConversations(chats => chats.map(chat => ({ ...chat, turns: chat.turns.map(turn => turn.answer !== null ? turn : { ...turn, ...getDemoReply(turn.question) }) }))), 0);
    return () => clearTimeout(timer);
  }, [conversations]);
  const pendingTurn = (question: string): ChatTurn => ({ id: crypto.randomUUID(), question, answer: null, sourceIds: [], relatedIds: [] });
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
