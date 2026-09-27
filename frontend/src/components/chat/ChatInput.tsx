import { useState } from 'react';
import { ArrowUp, Paperclip } from 'lucide-react';

export function ChatInput({ placeholder = 'Ask EKOS anything...', onSubmit, disabled = false }: { placeholder?: string; onSubmit: (question: string) => void; disabled?: boolean }) {
  const [question, setQuestion] = useState('');
  return <form className="chat-input" onSubmit={event => { event.preventDefault(); if (!disabled && question.trim()) { onSubmit(question.trim()); setQuestion(''); } }}>
    <button className="attachment-button" type="button" disabled aria-label="Attachments unavailable in this demo" title="Attachments are not part of this demo"><Paperclip size={21} /></button>
    <textarea rows={1} aria-label={placeholder} placeholder={placeholder} value={question} maxLength={2000} onChange={event => setQuestion(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} disabled={disabled} />
    <button className="send-button" type="submit" aria-label="Send message" disabled={disabled || !question.trim()}><ArrowUp size={21} /></button>
  </form>;
}
