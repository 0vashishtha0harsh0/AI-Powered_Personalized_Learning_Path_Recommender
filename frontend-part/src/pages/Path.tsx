import {
  Check, Lock, Play, Clock3, Sparkles, ArrowRight
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import SectionTitle from "../components/SectionTitle";
import ProgressBar from "../components/ProgressBar";
import { path, LearningPathItem } from "../data/mock";
import { completeMilestone, getCompletedMilestones } from "../state";

export default function Path() {
  const [completed, setCompleted] = useState(getCompletedMilestones);
  const [selected, setSelected] = useState<LearningPathItem>(path.find((item: LearningPathItem) => item.status === "current") || path[0] || {
    title: "No learning path yet",
    status: "current",
    type: "Getting started",
    time: "Complete onboarding first",
  });

  function continueSelected() {
    const index = path.findIndex((item: LearningPathItem) => item.title === selected.title);
    if (index < 0) return;
    completeMilestone(index + 1);
    setCompleted(getCompletedMilestones());
  }

  return (
    <>
      <SectionTitle
        title="Your learning path"
        text="An adaptive roadmap built around your goal, skills and progress."
      />

      <div className="path-layout">
        <div className="roadmap">
          <div className="roadmap-line" />
          {path.map((item, i) => (
            <button
              className={`path-node ${completed.includes(i + 1) ? "done" : item.status}`}
              key={item.title}
              onClick={() => setSelected(item)}
            >
              <div className="node-icon">
                {completed.includes(i + 1) && <Check size={17} />}
                {!completed.includes(i + 1) && item.status === "current" && <Play size={16} />}
                {!completed.includes(i + 1) && item.status === "locked" && <Lock size={15} />}
              </div>
              <div className="node-copy">
                <span>{item.type}</span>
                <h3>{item.title}</h3>
                <small><Clock3 size={13} /> {item.time}</small>
              </div>
              {item.progress && (
                <div className="node-progress">
                  <ProgressBar value={item.progress} />
                  <small>{item.progress}%</small>
                </div>
              )}
            </button>
          ))}
        </div>

        <aside className="path-detail card">
          <div className="ai-head">
            <div className="ai-icon"><Sparkles size={18} /></div>
            <div>
              <span className="tag">PATH NODE</span>
              <h3>{selected.title}</h3>
            </div>
          </div>

          <p className="muted">
            This milestone is positioned using your current skill level,
            target goal and prerequisite sequence.
          </p>

          {selected.progress && (
            <div className="detail-progress">
              <div><span>Progress</span><b>{selected.progress}%</b></div>
              <ProgressBar value={selected.progress} />
            </div>
          )}

          <div className="detail-box">
            <b>Why this is here</b>
            <span>✓ Fits your current level</span>
            <span>✓ Supports {selected.type.toLowerCase()}</span>
            <span>✓ Unlocks upcoming skills</span>
          </div>

          {selected.courses?.length ? <div className="detail-courses">
            <b>Recommended resources</b>
            {selected.courses.map(course => <a key={course.title} href={course.url || undefined} target="_blank" rel="noreferrer">
              <span>{course.title}</span><small>{course.source} · {Math.round(course.score * 100)}% match</small>
            </a>)}
          </div> : null}

          <button className="btn primary full" onClick={continueSelected}>
            {completed.includes(path.findIndex(item => item.title === selected.title) + 1) ? "Completed" : "Mark complete"}
            <ArrowRight size={16} />
          </button>
          {!path.length && <Link className="btn ghost full" to="/onboarding">Create my learning path</Link>}
        </aside>
      </div>
    </>
  );
}
