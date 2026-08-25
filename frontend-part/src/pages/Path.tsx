import {
  Check, Lock, Play, Clock3, Sparkles, ArrowRight
} from "lucide-react";
import { useState } from "react";
import SectionTitle from "../components/SectionTitle";
import ProgressBar from "../components/ProgressBar";
import { path } from "../data/mock";

export default function Path() {
  const [selected, setSelected] = useState(path[2]);

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
              className={`path-node ${item.status}`}
              key={item.title}
              onClick={() => setSelected(item)}
            >
              <div className="node-icon">
                {item.status === "done" && <Check size={17} />}
                {item.status === "current" && <Play size={16} />}
                {item.status === "locked" && <Lock size={15} />}
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

          <button className="btn primary full">
            {selected.status === "done" ? "Review module" : "Continue"} 
            <ArrowRight size={16} />
          </button>
        </aside>
      </div>
    </>
  );
}
