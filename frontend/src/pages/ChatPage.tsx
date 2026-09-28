import { WaitingStatus } from '../components/chat/WaitingStatus';
import { useEffect, useRef } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { RightPanel } from '../components/layout/RightPanel';
import { ContextSources } from '../components/chat/ContextSources';
import { ChatInput } from '../components/chat/ChatInput';
import { useChat } from '../hooks/useChat';
import { useAuth } from '../hooks/useAuth';
import { chatSourceUrl } from '../services/api';

export function ChatPage() {
  const { conversationId } = useParams();
  const { error: authError } = useAuth();
  const { conversations, sendFollowUp } = useChat();
  const chat = conversations.find(conversation => conversation.id === conversationId);
  const initialTurns = useRef(new Set(chat?.turns.filter(turn => turn.answer !== null).map(turn => turn.id)));
  const initialConversation = useRef(chat?.id);
  if (initialConversation.current !== chat?.id) {
    initialConversation.current = chat?.id;
    initialTurns.current = new Set(chat?.turns.filter(turn => turn.answer !== null).map(turn => turn.id));
  }
  const endRef = useRef<HTMLDivElement>(null);
  const last = chat?.turns.at(-1);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: 'end' }); }, [chat?.id, chat?.turns.length, last?.answer]);
  if (!chat) return <AppShell><div className="empty-page"><h1>Conversation not found</h1>{authError ? <><p className="inline-error" role="alert">{authError}</p><Link to="/login" className="text-link">Sign in</Link></> : <p className="state-message">This conversation is not saved in this browser session.</p>}<Link to="/" className="text-link">Start a new chat →</Link></div></AppShell>;
  return <AppShell className="chat-page" rightPanel={<RightPanel label="Conversation context"><ContextSources key={last?.id} sources={last?.sources || []} loading={last?.answer === null} /></RightPanel>}>
    <div className="conversation" aria-label="Conversation">
      {chat.turns.map(turn => <div className={`chat-turn ${initialTurns.current.has(turn.id) ? '' : 'new-turn'}`} key={turn.id}><div className="user-message">{turn.question}</div><div className="assistant-message"><div>
        {turn.answer === null ? <WaitingStatus /> : <>
          <div className={turn.mode === 'error' ? 'inline-error' : 'answer-copy'} role={turn.mode === 'error' ? 'alert' : undefined}>{turn.answer.split('\n\n').map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
          {turn.mode === 'sign-in' && <Link className="text-link" to="/login">Sign in →</Link>}
          {!!turn.sources.length && <section className="retrieved-knowledge" aria-label="Sources"><h2>Sources</h2>{turn.sources.map((source, index) => {
            const url = chatSourceUrl(source);
            return <article className="retrieval-result" key={index}><h3>{source.title || source.repository || 'Knowledge source'}</h3><p className="item-meta">{[source.repository, (source.entity_type || source.type || source.source || source.connector || 'document').replaceAll('_', ' ')].filter(Boolean).join(' · ')}</p><p className="retrieved-text">{source.snippet}</p>{url && <a className="text-link" href={url} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={14} /></a>}</article>;
          })}</section>}
        </>}
      </div></div></div>)}<div ref={endRef} />
    </div>
    <div className="follow-up-composer"><ChatInput key={chat.id} placeholder="Ask a follow-up..." disabled={last?.answer === null} onSubmit={question => sendFollowUp(chat.id, question)} /></div>
  </AppShell>;
}
