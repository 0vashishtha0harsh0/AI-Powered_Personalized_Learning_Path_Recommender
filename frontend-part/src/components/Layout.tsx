import React, { useEffect, useState } from "react";
import {
  NavLink,
  Outlet
} from "react-router-dom";

import {
  Brain,
  Home,
  Map,
  MessageCircle,
  BarChart3,
  UserRound,
  Menu,
  X,
  Target
} from "lucide-react";

import { getLearningData } from "../data/mock";
import { PATHAI_STATE_CHANGED } from "../state";
import { clearSession } from "../api";

const nav = [
  ["/", "Dashboard", Home],
  ["/path", "My Learning Path", Map],
  ["/mentor", "AI Mentor", MessageCircle],
  ["/skills", "Skill Map", Brain],
  ["/progress", "Progress", BarChart3],
  ["/profile", "Profile", UserRound]
];

export default function Layout() {
  const [open, setOpen] = useState(false);
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

  const { learner } = data;

  return (
    <div className="app">
      <aside className={open ? "sidebar show" : "sidebar"}>
        <div className="brand">
          <div className="logo"><Brain size={19} /></div>
          <span>PathAI</span>
          <button className="close" onClick={() => setOpen(false)}>
            <X size={19} />
          </button>
        </div>

        <div className="nav-label">Workspace</div>
        <nav>
          {nav.map(([to, label, Icon]: any) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="side-goal">
          <div className="mini-icon"><Target size={16} /></div>
          <small>Your current goal</small>
          <strong>{learner.goal}</strong>
          <div className="mini-progress">
            <span style={{ width: `${learner.progress}%` }} />
          </div>
          <small>{learner.progress}% complete</small>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="menu" onClick={() => setOpen(true)}>
            <Menu size={21} />
          </button>
          <div className="top-title">Learning workspace</div>
          <div className="top-user">
            <div className="avatar">A</div>
            <span>{learner.name}</span>
            <button className="signout" onClick={() => { clearSession(); window.location.href = "/login"; }}>Sign out</button>
          </div>
        </header>
        <div className="page"><Outlet /></div>
      </main>
    </div>
  );
}
