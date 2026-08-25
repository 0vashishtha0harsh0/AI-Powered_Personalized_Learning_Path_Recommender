import { ArrowRight, Brain, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

export default function Onboarding() {
  const [goal, setGoal] = useState("");
  const navigate = useNavigate();

  return (
    <main className="onboarding">
      <div className="onboard-glow" />
      <div className="onboard-logo"><Brain size={19} /> PathAI</div>
      <div className="onboard-content">
        <span className="eyebrow"><Sparkles size={14} /> AI-POWERED LEARNING</span>
        <h1>Your goal.<br /><em>Your path.</em></h1>
        <p>
          Tell PathAI where you want to go. We'll turn your skills,
          experience and goals into a personalized learning journey.
        </p>
        <div className="goal-input">
          <textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="I want to become an AI Engineer in 6 months..."
          />
          <button onClick={() => navigate("/")} disabled={!goal.trim()}>
            Build my path <ArrowRight size={17} />
          </button>
        </div>
        <div className="examples">
          <span>Try:</span>
          <button onClick={() => setGoal("I want to become a Generative AI Engineer.")}>
            Generative AI Engineer
          </button>
          <button onClick={() => setGoal("I want to become a Full Stack Developer.")}>
            Full Stack Developer
          </button>
        </div>
      </div>
    </main>
  );
}
