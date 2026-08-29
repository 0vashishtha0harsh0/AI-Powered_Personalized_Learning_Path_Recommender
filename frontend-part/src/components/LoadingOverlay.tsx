import { Loader2 } from "lucide-react";
import { createPortal } from "react-dom";

type LoadingOverlayProps = {
  show: boolean;
  title?: string;
  message?: string;
};

export default function LoadingOverlay({
  show,
  title = "Working on it",
  message = "Please wait while we finish this step.",
}: LoadingOverlayProps) {
  if (!show) return null;

  return createPortal(
    <div className="loading-overlay" role="status" aria-live="polite" aria-busy="true">
      <div className="loading-panel">
        <Loader2 className="spin" size={34} />
        <h2>{title}</h2>
        <p>{message}</p>
        <div className="loading-bar"><span /></div>
      </div>
    </div>,
    document.body,
  );
}
