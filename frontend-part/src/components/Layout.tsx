import React, { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  BookOpen,
  Home,
  Map,
  MessageCircle,
  BarChart3,
  UserRound,
  Menu,
  X,
} from "lucide-react";
import { getLearningData } from "../data/mock";
import { PATHAI_STATE_CHANGED } from "../state";
import { clearSession } from "../api";

const nav = [
  ["/", "Dashboard", Home],
  ["/path", "My Path", Map],
  ["/mentor", "Mentor", MessageCircle],
  ["/skills", "Skills", BookOpen],
  ["/progress", "Progress", BarChart3],
  ["/profile", "Profile", UserRound],
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
          <div className="logo"><BookOpen size={17} /></div>
          <span>PathAI</span>
          <button className="close" onClick={() => setOpen(false)}>
            <X size={18} />
          </button>
        </div>

        <div className="nav-label">Navigation</div>
        <nav>
          {nav.map(([to, label, Icon]: any) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

      </aside>

      <main className="main">
        <header className="topbar">
          <button className="menu" onClick={() => setOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="top-title">Learning workspace</div>
          <div className="top-user">
            <div className="avatar">{(learner.name || "U")[0].toUpperCase()}</div>
            <span>{learner.name}</span>
            <button className="signout" onClick={() => { clearSession(); window.location.href = "/login"; }}>Sign out</button>
          </div>
        </header>
        <div className="page"><Outlet /></div>
      </main>
    </div>
  );
}
