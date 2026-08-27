import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Path from "./pages/Path";
import Mentor from "./pages/Mentor";
import Skills from "./pages/Skills";
import Progress from "./pages/Progress";
import Profile from "./pages/Profile";
import Onboarding from "./pages/Onboarding";
import Login from "./pages/Login";
import { getToken } from "./api";
import { Navigate } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/path" element={<Path />} />
        <Route path="/mentor" element={<Mentor />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}
