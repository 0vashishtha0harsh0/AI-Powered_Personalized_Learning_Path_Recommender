import { Bot, Send, Sparkles, User } from "lucide-react";
import { useState } from "react";

const starters = [
  "Why is Deep Learning next?",
  "What should I learn before CNNs?",
  "Test my ML knowledge",
  "Can I skip this module?"
];

export default function Mentor() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      ai: true,
      text: "Hey! I know your goal, progress and current skill gaps. What do you want to figure out?"
    }
  ]);

  function send(text = input) {
    if (!text.trim()) return;
    setMessages(v => [
      ...v,
      { ai: false, text },
      {
        ai: true,
        text: "Based on your current profile, Deep Learning is the best next step. It closes your largest gap while building directly on your ML foundation."
      }
    ]);
    setInput("");
  }

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

      <div className="chat card">
        <div className="messages">
          {messages.map((m, i) => (
            <div className={m.ai ? "message ai" : "message user"} key={i}>
              <div className="message-icon">
                {m.ai ? <Sparkles size={15} /> : <User size={15} />}
              </div>
              <p>{m.text}</p>
            </div>
          ))}
        </div>

        <div className="quick">
          {starters.map(s => (
            <button key={s} onClick={() => send(s)}>{s}</button>
          ))}
        </div>

        <div className="chat-input">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Ask PathAI anything..."
          />
          <button onClick={() => send()}><Send size={17} /></button>
        </div>
      </div>
    </div>
  );
}
