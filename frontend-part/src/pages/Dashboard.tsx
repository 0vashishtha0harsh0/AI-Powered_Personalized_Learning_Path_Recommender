import {
  ArrowRight, Clock3, Flame, Sparkles, Target, Trophy
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ProgressBar from "../components/ProgressBar";
import SectionTitle from "../components/SectionTitle";
import { getLearningData } from "../data/mock";
import { PATHAI_STATE_CHANGED } from "../state";

export default function Dashboard() {
  const [data, setData] = useState(() => getLearningData());

  useEffect(() => {
    const refresh = () => setData(getLearningData());
    window.addEventListener(PATHAI_STATE_CHANGED, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(PATHAI_STATE_CHANGED, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  const { learner, recommendations, skills, completion, completedMilestones } = data;
  const next = recommendations[0] || {
    title: "Build your learning path",
    reason: "Complete onboarding to get recommendations for your goal.",
    time: "Not started",
    level: "PathAI",
  };

  return (
    <>
      <div className="hero">
        <div>
          <span className="eyebrow">PERSONALIZED LEARNING</span>
          <h1>Good evening, {learner.name} <span>✦</span></h1>
          <p>Your personalized journey is built around this goal.</p>
        </div>
        <Link className="btn ghost" to="/mentor">
          <Sparkles size={16} /> Ask PathAI
        </Link>
      </div>

      <div className="goal-card">
        <div>
          <div className="goal-top">
            <span>YOUR GOAL</span>
            <strong>{learner.goal}</strong>
            <small className="career-match">Recommended career: {savedCareerTitle()}</small>
          </div>
          <div className="big-progress">
            <span style={{ width: `${completion}%` }} />
          </div>
          <div className="goal-bottom">
            <b>{completion}% complete</b>
            <span>{completedMilestones.length} of {learner.milestones} milestones complete</span>
          </div>
        </div>
        <div className="goal-orb">✦</div>
      </div>

      <div className="stats">
        <Stat icon={<Flame />} value={`${learner.streak} days`} label="Learning streak" />
        <Stat icon={<Clock3 />} value={`${learner.hours}h`} label="Learning time" />
        <Stat icon={<Trophy />} value={learner.milestones} label="Milestones" />
        <Stat icon={<Target />} value={`${Math.min(100, completion + (learner.milestones ? 10 : 0))}%`} label="Career readiness" />
      </div>

      <div className="grid-2">
        <div className="card next-card">
          <SectionTitle title="Your next best action" />
          <div className="next-head">
            <div className="course-icon"><Sparkles size={21} /></div>
            <div>
              <span className="tag">RECOMMENDED NEXT</span>
              <h3>{next.title}</h3>
            </div>
          </div>
          <p className="muted">{next.reason}</p>
          <div className="meta">
            <span><Clock3 size={15} /> {next.time}</span>
            <span>● {next.level}</span>
          </div>
          <Link className="btn primary full" to="/path">
            Start learning <ArrowRight size={16} />
          </Link>
        </div>

        <div className="card ai-card">
          <div className="ai-head">
            <div className="ai-icon"><Sparkles size={18} /></div>
            <div>
              <span className="tag">PATHAI INSIGHT</span>
              <h3>Why this recommendation?</h3>
            </div>
          </div>
          <p>
            Your recommendations are generated from your target occupation,
            current skills and identified learning gaps.
          </p>
          <div className="reason-list">
            <span>✓ Matches your target role</span>
            <span>✓ Builds on completed prerequisites</span>
            <span>✓ Addresses your highest-priority skill gap</span>
          </div>
          <Link to="/mentor" className="text-link">
            Ask PathAI about this <ArrowRight size={15} />
          </Link>
        </div>
      </div>

      <div className="card">
        <SectionTitle
          title="Skill fingerprint"
          text="Your current strengths and development areas"
        />
        <div className="skill-list">
          {skills.map(([name, value]) => (
            <div className="skill-row" key={name}>
              <div className="skill-name">
                <span>{name}</span><b>{value}%</b>
              </div>
              <ProgressBar value={value as number} />
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function savedCareerTitle() {
  try {
    const email = localStorage.getItem("pathai.email") || "anonymous";
    return JSON.parse(localStorage.getItem(`pathai.recommendation.v3.${email}`) || "{}").target_career?.title || "Pending profile";
  } catch {
    return "Pending profile";
  }
}

function Stat({ icon, value, label }: any) {
  return (
    <div className="stat">
      <div className="stat-icon">{icon}</div>
      <div><strong>{value}</strong><span>{label}</span></div>
    </div>
  );
}
