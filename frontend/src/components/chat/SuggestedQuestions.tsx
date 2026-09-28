import { Sparkle } from 'lucide-react';
import { suggestedQuestions } from '../../data/demoData';
import { PanelCard } from '../layout/RightPanel';
import { useChat } from '../../hooks/useChat';

export function SuggestedQuestions({ onSelect }: { onSelect?: (question: string) => void }) {
  const { startChat } = useChat();
  return <PanelCard className="suggestions-card"><h2 className="card-heading">Try Asking</h2><div className="suggestions">{suggestedQuestions.map(question => <button key={question} onClick={() => (onSelect || startChat)(question)} className="suggestion-row"><Sparkle size={15} aria-hidden="true" /><span>{question}</span></button>)}</div></PanelCard>;
}
