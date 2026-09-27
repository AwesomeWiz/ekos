import { useEffect, useRef } from 'react';
import { ArrowUpRight, LoaderCircle } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { RightPanel } from '../components/layout/RightPanel';
import { ContextSources } from '../components/chat/ContextSources';
import { RelatedKnowledge } from '../components/chat/RelatedKnowledge';
import { ChatInput } from '../components/chat/ChatInput';
import { entities, entityHref } from '../data/demoData';
import { useChat } from '../hooks/useChat';
import { sourceUrl } from '../services/api';

export function ChatPage() {
  const { conversationId } = useParams();
  const { conversations, sendFollowUp } = useChat();
  const chat = conversations.find(conversation => conversation.id === conversationId);
  const endRef = useRef<HTMLDivElement>(null);
  const last = chat?.turns.at(-1);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: 'end' }); }, [chat?.id, chat?.turns.length, last?.answer]);
  if (!chat) return <AppShell><div className="empty-page"><h1>Conversation not found</h1><p className="state-message">This conversation is not saved in this browser session.</p><Link to="/" className="text-link">Start a new chat →</Link></div></AppShell>;
  return <AppShell className="chat-page" rightPanel={<RightPanel label="Conversation context"><ContextSources sourceIds={last?.sourceIds || []} results={last?.mode && last.mode !== 'sample' ? last.results || [] : undefined} /><RelatedKnowledge relatedIds={last?.relatedIds || []} /></RightPanel>}>
    <div className="conversation" aria-label="Conversation"><p className="demo-caption">{!last?.mode || last.mode === 'sample' ? 'Sample conversation' : 'Semantic search · No AI-generated answers'}</p>
      {chat.turns.map(turn => <div className="chat-turn" key={turn.id}><div className="user-message">{turn.question}</div><div className="assistant-message"><div>
        {turn.answer !== null && (!turn.mode || turn.mode === 'sample') && <p className="demo-caption">Sample answer</p>}
        {turn.answer === null ? <p className="state-message" role="status"><LoaderCircle className="spinner" size={16} />Searching indexed knowledge…</p> : <>
          <div className={turn.mode === 'error' ? 'inline-error' : 'answer-copy'} role={turn.mode === 'error' ? 'alert' : undefined}>{turn.answer.split('\n\n').map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
          {turn.mode === 'empty-index' && <Link className="text-link" to="/connectors">Open Connectors →</Link>}
          {turn.mode === 'sign-in' && <Link className="text-link" to="/login">Sign in →</Link>}
          {!!turn.results?.length && <section className="retrieved-knowledge" aria-label="Retrieved knowledge"><h2>Retrieved knowledge</h2>{turn.results.map(result => {
            const url = sourceUrl(result);
            return <article className="retrieval-result" key={result.document_id}><h3>{String(result.metadata.title || result.metadata.entity_id || 'GitHub knowledge')}</h3><p className="item-meta">{result.metadata.repository} · {String(result.metadata.entity_type || 'document').replaceAll('_', ' ')}</p><p className="retrieved-text">{result.text}</p>{url && <a className="text-link" href={url} target="_blank" rel="noopener noreferrer">View GitHub source <ArrowUpRight size={14} /></a>}</article>;
          })}</section>}
          {turn.sourceIds.length > 0 && <div className="citations" aria-label="Sample references">{turn.sourceIds.map((id, index) => <Link key={id} to={entityHref(id)}>[{index + 1}] {entities[id].name}<ArrowUpRight size={14} /></Link>)}</div>}
        </>}
      </div></div></div>)}<div ref={endRef} />
    </div>
    <div className="follow-up-composer"><ChatInput key={chat.id} placeholder="Ask a follow-up..." disabled={last?.answer === null} onSubmit={question => sendFollowUp(chat.id, question)} /></div>
  </AppShell>;
}
