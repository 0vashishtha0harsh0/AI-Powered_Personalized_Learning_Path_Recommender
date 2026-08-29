import { Edit3, Target, UserRound } from "lucide-react";
import { useState } from "react";
import SectionTitle from "../components/SectionTitle";
import { getLearningData } from "../data/mock";
import { getProfile, saveProfile } from "../state";

export default function Profile() {
  const saved = getProfile();
  const [data, setData] = useState(() => getLearningData());
  const { learner, skills } = data;
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(saved.name || learner.name);
  const [level, setLevel] = useState(saved.level || learner.level);
  const [style, setStyle] = useState(saved.style || learner.style);

  function save() {
    const nextName = name.trim() || learner.name;
    saveProfile({ name: nextName, level, style });
    setData(getLearningData());
    setEditing(false);
  }

  return (
    <>
      <SectionTitle title="Learner profile" text="Your profile helps personalize your learning journey." />

      <div className="profile-card card">
        <div className="profile-avatar"><UserRound size={31} /></div>
        <div>
          <span className="tag">PROFILE</span>
          {editing ? <input className="profile-input" value={name} onChange={e => setName(e.target.value)} /> : <h2>{learner.name}</h2>}
          <p className="muted">{editing ? `${level} · ${style}` : `${learner.level} · ${learner.style}`}</p>
        </div>
        {editing ? <button className="btn primary" onClick={save}>Save profile</button> : <button className="btn ghost" onClick={() => setEditing(true)}><Edit3 size={15} /> Edit profile</button>}
      </div>

      {editing && <div className="profile-editor card">
        <label>Experience level<select value={level} onChange={e => setLevel(e.target.value)}><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label>
        <label>Learning style<input value={style} onChange={e => setStyle(e.target.value)} /></label>
      </div>}

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
            {[learner.goal, ...skills.slice(0, 4).map(([name]) => name)].filter((item, index, list) => item && list.indexOf(item) === index).map(x =>
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
