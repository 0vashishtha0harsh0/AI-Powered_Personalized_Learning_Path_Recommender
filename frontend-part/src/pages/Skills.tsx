import { AlertTriangle, Brain, Sparkles } from "lucide-react";
import ProgressBar from "../components/ProgressBar";
import SectionTitle from "../components/SectionTitle";
import { skillGaps, skills } from "../data/mock";
import { useNavigate } from "react-router-dom";

export default function Skills() {
  const navigate = useNavigate();
  return (
    <>
      <SectionTitle
        title="Skill map"
        text="A live view of your strengths and learning gaps."
      />

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div><span className="tag">SKILL FINGERPRINT</span><h3>Current abilities</h3></div>
            <Brain size={20} />
          </div>
          <div className="skill-list large">
            {skills.map(([name, value]) => (
              <div className="skill-row" key={name}>
                <div className="skill-name"><span>{name}</span><b>{value}%</b></div>
                <ProgressBar value={value as number} />
              </div>
            ))}
          </div>
        </div>

        <div className="card gap-card">
          <div className="ai-head">
            <div className="warning-icon"><AlertTriangle size={18} /></div>
            <div><span className="tag">AI DETECTED</span><h3>Skill gaps</h3></div>
          </div>
          <p className="muted">
            These areas have the highest impact on your target career.
          </p>
          {skillGaps.slice(0, 8).map(([name, value]) => (
            <div className="gap" key={name}>
              <div><span>{name}</span><b>{value}%</b></div>
              <ProgressBar value={value as number} />
            </div>
          ))}
          <button className="btn primary full" onClick={() => navigate("/path")}>
            <Sparkles size={16} /> Build gap plan
          </button>
        </div>
      </div>
    </>
  );
}
