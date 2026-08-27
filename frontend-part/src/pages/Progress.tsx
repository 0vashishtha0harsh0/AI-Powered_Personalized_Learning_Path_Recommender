import { Flame, Target, Trophy } from "lucide-react";
import {
  BarChart, Bar, XAxis, ResponsiveContainer, Tooltip
} from "recharts";
import SectionTitle from "../components/SectionTitle";
import { getLearningData, weekly } from "../data/mock";

export default function Progress() {
  const { learner, path, completedMilestones: completed, completion } = getLearningData();
  return (
    <>
      <SectionTitle
        title="Progress"
        text="Track learning momentum, milestones and career readiness."
      />

      <div className="stats">
        <Stat icon={<Target />} value={`${completion}%`} label="Path complete" />
        <Stat icon={<Flame />} value={`${learner.streak} days`} label="Current streak" />
        <Stat icon={<Trophy />} value={`${Math.min(100, completion + 10)}%`} label="Career readiness" />
      </div>

      <div className="grid-2">
        <div className="card chart-card">
          <div className="card-head">
            <div><span className="tag">THIS WEEK</span><h3>Learning activity</h3></div>
            <b>{learner.hours}h</b>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weekly}>
                <XAxis dataKey="day" axisLine={false} tickLine={false} />
                <Tooltip cursor={{ opacity: .08 }} />
                <Bar dataKey="hours" radius={[6, 6, 2, 2]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <span className="tag">MILESTONES</span>
          <h3>Journey checkpoints</h3>
          <div className="timeline">
            {path.length ? path.map((item, index) => {
              const done = completed.includes(index + 1);
              return (
              <div className="timeline-item" key={`${item.type}-${index}`}>
                <span className={done ? "dot done" : "dot"} />
                <div><b>{item.type}</b><small>{done ? "Completed" : index === completed.length ? "Current" : "Upcoming"}</small></div>
              </div>
              );
            }) : <p className="muted">Complete onboarding to create your milestones.</p>}
          </div>
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
