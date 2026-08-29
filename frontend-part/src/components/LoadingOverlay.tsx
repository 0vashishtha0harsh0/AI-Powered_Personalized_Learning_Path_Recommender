import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

type LoadingOverlayProps = {
  show: boolean;
  title?: string;
  message?: string;
};

const followUpMessages = [
  "Still working. Some recommendations can take a little longer to prepare.",
  "Matching your goal with career signals and skill gaps.",
  "Checking the best learning steps for your current profile.",
  "Almost there. We are organizing your path and resources.",
];

export default function LoadingOverlay({
  show,
  title = "Working on it",
  message = "Please wait while we finish this step.",
}: LoadingOverlayProps) {
  const messages = useMemo(() => {
    return [message, ...followUpMessages.filter(item => item !== message)];
  }, [message]);
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    setMessageIndex(0);
  }, [message, show]);

  useEffect(() => {
    if (!show || messages.length < 2) return;

    const timer = window.setInterval(() => {
      setMessageIndex(index => (index + 1) % messages.length);
    }, 6500);

    return () => window.clearInterval(timer);
  }, [messages.length, show]);

  if (!show) return null;

  return createPortal(
    <div className="loading-overlay" role="status" aria-live="polite" aria-busy="true">
      <div className="loading-panel">
        <Loader2 className="spin" size={34} />
        <h2>{title}</h2>
        <p key={messages[messageIndex]}>{messages[messageIndex]}</p>
        <div className="loading-bar"><span /></div>
      </div>
    </div>,
    document.body,
  );
}
