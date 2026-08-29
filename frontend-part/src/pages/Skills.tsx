import { AlertTriangle, BarChart3, Zap } from "lucide-react";
import { useState } from "react";
import ProgressBar from "../components/ProgressBar";
import SectionTitle from "../components/SectionTitle";
import { getLearningData } from "../data/mock";
import { useNavigate } from "react-router-dom";
import { createRecommendation, saveLearnerProfile, saveRecommendation } from "../api";
import { getStoredGoal, getStoredSkills } from "../state";

export default function Skills() {
  const navigate = useNavigate();
  const [data, setData] = useState(() => getLearningData());
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState("");
  const { skillGaps, skills } = data;

  async function buildGapPlan() {
    const goal = getStoredGoal();
    const currentSkills = getStoredSkills();
    if (!goal.trim()) {
      navigate("/onboarding");
      return;
    }

    setBusy(true);
    setError("");
    try {
      setPhase("Reading profile");
      await new Promise(resolve => setTimeout(resolve, 300));
      setPhase("Analyzing skill gaps");
      await saveLearnerProfile(goal, currentSkills);
      setPhase("Matching courses from dataset");
      const recommendation = await createRecommendation(goal, currentSkills);
      setPhase("Building gap plan");
      saveRecommendation(recommendation);
      setData(getLearningData());
      navigate("/path");
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Could not build gap plan.";
      if (message.toLowerCase().includes("session expired")) {
        navigate("/login", { replace: true });
        return;
      }
      setError(message);
      setBusy(false);
      setPhase("");
    }
  }

  return (
    <>
      <SectionTitle
        title="Skill map"
        text="A live view of your strengths and learning gaps."
      />

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div><span className="tag">CURRENT SKILLS</span><h3>Abilities</h3></div>
            <BarChart3 size={20} />
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
          {error && <p className="form-error">{error}</p>}
          {skillGaps.slice(0, 8).map(([name, value]) => (
            <div className="gap" key={name}>
              <div><span>{name}</span><b>{value}%</b></div>
              <ProgressBar value={value as number} />
            </div>
          ))}
          <button className="btn primary full" onClick={buildGapPlan} disabled={busy}>
            <Zap size={15} /> {busy ? phase || "Building plan" : "Build learning plan"}
          </button>
        </div>
      </div>
    </>
  );
}
