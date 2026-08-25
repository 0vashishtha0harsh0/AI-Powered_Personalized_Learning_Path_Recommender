import {
  ArrowRight, Clock3, Flame, Sparkles, Target, Trophy
} from "lucide-react";
import { Link } from "react-router-dom";
import ProgressBar from "../components/ProgressBar";
import SectionTitle from "../components/SectionTitle";
import { learner, recommendations, skills } from "../data/mock";

export default function Dashboard() {
  const next = recommendations[0];

  return (
    <>
      <div className="hero">
        <div>
          <span className="eyebrow">PERSONALIZED LEARNING</span>
          <h1>Good evening, {learner.name} <span>✦</span></h1>
          <p>Your AI Engineer journey is moving forward.</p>
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
          </div>
          <div className="big-progress">
            <span style={{ width: `${learner.progress}%` }} />
          </div>
          <div className="goal-bottom">
            <b>{learner.progress}% complete</b>
            <span>68 of 160 learning hours</span>
          </div>
        </div>
        <div className="goal-orb">✦</div>
      </div>

      <div className="stats">
        <Stat icon={<Flame />} value={`${learner.streak} days`} label="Learning streak" />
        <Stat icon={<Clock3 />} value={`${learner.hours}h`} label="Learning time" />
        <Stat icon={<Trophy />} value={learner.milestones} label="Milestones" />
        <Stat icon={<Target />} value="71%" label="Career readiness" />
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
            Your ML fundamentals are strong, but Deep Learning is currently
            your largest skill gap for the target role.
          </p>
          <div className="reason-list">
            <span>✓ Matches your target role</span>
            <span>✓ Builds on completed prerequisites</span>
            <span>✓ Addresses your biggest skill gap</span>
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

function Stat({ icon, value, label }: any) {
  return (
    <div className="stat">
      <div className="stat-icon">{icon}</div>
      <div><strong>{value}</strong><span>{label}</span></div>
    </div>
  );
}
