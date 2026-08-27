import { Bot, Send, Sparkles, User, Loader2, AlertTriangle } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { API_URL, clearSession, getToken } from "../api";

const starters = [
  "Why is Deep Learning next?",
  "What should I learn before CNNs?",
  "Test my ML knowledge",
  "Can I skip this module?"
];

type Message = { role: "user" | "assistant"; content: string };

function getRecommendationContext() {
  try {
    const email = localStorage.getItem("pathai.email") || "anonymous";
    const raw = localStorage.getItem(`pathai.recommendation.v3.${email}`);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export default function Mentor() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hey! I know your goal, progress and current skill gaps. What do you want to figure out?"
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mentorConfigured, setMentorConfigured] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    fetch(`${API_URL}/mentor/status`)
      .then(r => r.json())
      .then(data => setMentorConfigured(data.configured))
      .catch(() => setMentorConfigured(null));
  }, []);

  async function send(text = input) {
    if (!text.trim() || loading) return;

    const userMessage: Message = { role: "user", content: text.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const conversationHistory = newMessages.slice(1).map(m => ({
        role: m.role,
        content: m.content,
      }));

      const recommendationContext = getRecommendationContext();

      const response = await fetch(`${API_URL}/mentor/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken() || ""}`,
        },
        body: JSON.stringify({
          question: text.trim(),
          conversation_history: conversationHistory,
          recommendation_context: recommendationContext,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) {
          clearSession();
          throw new Error("Your session expired. Please sign in again.");
        }
        throw new Error(body.detail || "Could not get a response from the AI Mentor.");
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Something went wrong.";
      setError(errorMsg);
      const showConfigurationHint =
        /not configured|GEMINI_API_KEY|API key|Gemini API error/i.test(errorMsg);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: showConfigurationHint
          ? `⚠️ ${errorMsg}\n\nThe backend reports the mentor provider could not be used. Check \`GEMINI_API_KEY\` and the selected \`LLM_MODEL\` on Render, then redeploy.`
          : `⚠️ ${errorMsg}`
      }]);
    } finally {
      setLoading(false);
    }
  }

  const notConfigured = mentorConfigured === false;

  return (
    <div className="mentor-page">
      <div className="mentor-title">
        <div className="ai-icon large"><Bot size={25} /></div>
        <div>
          <span className="eyebrow">YOUR LEARNING COPILOT</span>
          <h1>PathAI Mentor</h1>
          <p>Ask questions about your path, skills or next steps.</p>
        </div>
      </div>

      {notConfigured && (
        <div className="card" style={{ marginBottom: 16, padding: 16, display: "flex", gap: 10, alignItems: "center", borderColor: "#fbbf24" }}>
          <AlertTriangle size={18} style={{ color: "#fbbf24", flexShrink: 0 }} />
          <div style={{ fontSize: 13, color: "#cbd2dd" }}>
            <strong style={{ color: "#fbbf24" }}>AI Mentor not configured.</strong>{" "}
            Set <code style={{ background: "#1a2030", padding: "2px 6px", borderRadius: 4, fontSize: 12 }}>GEMINI_API_KEY</code> on the backend server to enable AI-powered mentoring.
            <br /><span style={{ fontSize: 11, color: "#8c96a8" }}>Get your key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" style={{ color: "#a78bfa" }}>aistudio.google.com/apikey</a></span>
          </div>
        </div>
      )}

      <div className="chat card">
        <div className="messages">
          {messages.map((m, i) => (
            <div className={m.role === "assistant" ? "message ai" : "message user"} key={i}>
              <div className="message-icon">
                {m.role === "assistant" ? <Sparkles size={15} /> : <User size={15} />}
              </div>
              <p style={{ whiteSpace: "pre-wrap" }}>{m.content}</p>
            </div>
          ))}
          {loading && (
            <div className="message ai">
              <div className="message-icon"><Sparkles size={15} /></div>
              <p style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Loader2 size={14} className="spin" /> Thinking...
              </p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {messages.length <= 1 && (
          <div className="quick">
            {starters.map(s => (
              <button key={s} onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}

        <div className="chat-input">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !loading && send()}
            placeholder={notConfigured ? "Set GEMINI_API_KEY on backend to enable" : "Ask PathAI anything..."}
            disabled={loading}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}>
            {loading ? <Loader2 size={17} className="spin" /> : <Send size={17} />}
          </button>
        </div>
      </div>
    </div>
  );
}
