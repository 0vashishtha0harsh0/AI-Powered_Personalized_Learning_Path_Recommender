import { ArrowRight, Brain, LockKeyhole, Mail } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authenticate } from "../api";

export default function Login() {
  const navigate = useNavigate();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authenticate(email, password, register);
      const emailKey = `pathai.recommendation.v3.${email.trim().toLowerCase()}`;
      navigate(register || !localStorage.getItem(emailKey) ? "/onboarding" : "/", { replace: true });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Authentication failed.");
      setLoading(false);
    }
  }

  return <main className="auth-page">
    <div className="auth-panel">
      <div className="onboard-logo"><div className="logo"><Brain size={19} /></div> PathAI</div>
      <span className="eyebrow">PERSONALIZED LEARNING WORKSPACE</span>
      <h1>{register ? "Create your learning account." : "Welcome back to your path."}</h1>
      <p className="muted">Your account keeps your goal, skills, progress and recommendations together.</p>
      <form onSubmit={submit}>
        <label><Mail size={15} /> Email<input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label>
        <label><LockKeyhole size={15} /> Password<input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 8 characters" /></label>
        {error && <p className="form-error">{error}</p>}
        <button className="btn primary full" disabled={loading}>{loading ? "Please wait..." : register ? "Create account" : "Sign in"}<ArrowRight size={16} /></button>
      </form>
      <button className="auth-switch" onClick={() => { setRegister(!register); setError(""); }}>
        {register ? "Already have an account? Sign in" : "New to PathAI? Create an account"}
      </button>
    </div>
  </main>;
}