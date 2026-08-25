import { Edit3, Target, UserRound } from "lucide-react";
import SectionTitle from "../components/SectionTitle";
import { learner, skills } from "../data/mock";

export default function Profile() {
  return (
    <>
      <SectionTitle title="Learner profile" text="The context PathAI uses to personalize your journey." />

      <div className="profile-card card">
        <div className="profile-avatar"><UserRound size={31} /></div>
        <div>
          <span className="tag">LEARNER</span>
          <h2>{learner.name}</h2>
          <p className="muted">{learner.level} · {learner.style}</p>
        </div>
        <button className="btn ghost"><Edit3 size={15} /> Edit profile</button>
      </div>

      <div className="grid-2">
        <div className="card">
          <span className="tag">PRIMARY GOAL</span>
          <div className="profile-goal">
            <Target size={21} />
            <div><h3>{learner.goal}</h3><p>Become job-ready in 6 months</p></div>
          </div>
        </div>
        <div className="card">
          <span className="tag">INTERESTS</span>
          <div className="chips">
            {["AI", "Machine Learning", "Python", "Computer Vision", "GenAI"].map(x =>
              <span key={x}>{x}</span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <span className="tag">CURRENT SKILLS</span>
        <div className="chips skill-chips">
          {skills.map(([name, value]) => <span key={name}>{name} · {value}%</span>)}
        </div>
      </div>
    </>
  );
}
