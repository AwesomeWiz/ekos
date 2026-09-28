import { useEffect, useState } from 'react';

const waitingCopy = ['Thinking it through', 'Working on your answer', 'Putting it together'];
export function WaitingStatus() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const preference = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    let timer: ReturnType<typeof setInterval> | undefined;
    const update = () => {
      clearInterval(timer);
      if (!preference?.matches) timer = setInterval(() => setStep(value => (value + 1) % waitingCopy.length), 3200);
    };
    update(); preference?.addEventListener('change', update);
    return () => { clearInterval(timer); preference?.removeEventListener('change', update); };
  }, []);
  return <div className="waiting-status state-message" role="status" aria-label="Waiting for an answer">
    <span className="waiting-dot" aria-hidden="true" /><span key={step} aria-hidden="true" className="waiting-copy">{waitingCopy[step]}…</span>
  </div>;
}
