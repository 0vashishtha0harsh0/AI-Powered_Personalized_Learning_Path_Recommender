import { ArrowRight, Brain, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { createRecommendation, getSkills, saveLearnerProfile, saveRecommendation } from "../api";
import { saveProfile } from "../state";

export default function Onboarding() {
  const [goal, setGoal] = useState("");
  const [skillOptions, setSkillOptions] = useState<Array<{ id: string; label: string }>>([]);
  const [skillSearch, setSkillSearch] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<Array<{ label: string; level: string }>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [buildPhase, setBuildPhase] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getSkills().then(setSkillOptions).catch(() => setSkillOptions([]));
  }, []);

  async function buildPath() {
    if (!goal.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const skills = selectedSkills.map(skill => skill.label);
      const accountEmail = localStorage.getItem("pathai.email") || "anonymous";
      localStorage.setItem(`pathai.skills.${accountEmail}`, JSON.stringify(skills));
      localStorage.setItem(`pathai.skillLevels.${accountEmail}`, JSON.stringify(selectedSkills));
      localStorage.setItem(`pathai.goal.${accountEmail}`, goal.trim());
      saveProfile({ name: accountEmail.split("@")[0] || "Learner", level: "Intermediate", style: "Hands-on · Project-based" });
      setBuildPhase("Reading your goal");
      await new Promise(resolve => setTimeout(resolve, 450));
      setBuildPhase("Mapping your skills");
      await saveLearnerProfile(goal.trim(), skills);
      setBuildPhase("Ranking careers and skill gaps");
      const recommendation = await createRecommendation(goal.trim(), skills);
      setBuildPhase("Ordering your milestones");
      saveRecommendation(recommendation);
      navigate("/", { replace: true });
      window.location.reload();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not build your path.");
      setLoading(false);
      setBuildPhase("");
    }
  }

  return (
    <main className="onboarding">
      <div className="onboard-glow" />
      <div className="onboard-logo"><Brain size={19} /> PathAI</div>
      <div className="onboard-content">
        <span className="eyebrow"><Sparkles size={14} /> AI-POWERED LEARNING</span>
        <h1>Your goal.<br /><em>Your path.</em></h1>
        <p>
          Tell PathAI where you want to go. We'll turn your skills,
          experience and goals into a personalized learning journey.
        </p>
        <div className="goal-input">
          <textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="I want to become an AI Engineer in 6 months..."
          />
          <input
            className="onboard-skills"
            value={skillSearch}
            onChange={e => setSkillSearch(e.target.value)}
            placeholder="Search your current skills..."
          />
          <div className="skill-picker">
            <div className="selected-skills">{selectedSkills.map(skill => (
              <div className="selected-skill" key={skill.label}>
                <span>{skill.label}</span>
                <select value={skill.level} onChange={event => setSelectedSkills(selectedSkills.map(item => item.label === skill.label ? { ...item, level: event.target.value } : item))}>
                  <option>Beginner</option><option>Intermediate</option><option>Advanced</option>
                </select>
                <button type="button" onClick={() => setSelectedSkills(selectedSkills.filter(item => item.label !== skill.label))}>×</button>
              </div>
            ))}</div>
            {skillOptions.filter(skill => skill.label.toLowerCase().includes(skillSearch.toLowerCase())).slice(0, 12).map(skill => (
              <button type="button" className="skill-option" key={skill.id} onClick={() => !selectedSkills.some(item => item.label === skill.label) && setSelectedSkills([...selectedSkills, { label: skill.label, level: "Intermediate" }])}>{skill.label}</button>
            ))}
          </div>
          <button onClick={buildPath} disabled={!goal.trim() || loading}>
            {loading ? buildPhase || "Building..." : "Build my path"} <ArrowRight size={17} />
          </button>
        </div>
        {error && <p className="form-error">{error}</p>}
        <div className="examples">
          <span>Try:</span>
          <button onClick={() => setGoal("I want to become a Generative AI Engineer.")}>
            Generative AI Engineer
          </button>
          <button onClick={() => setGoal("I want to become a Full Stack Developer.")}>
            Full Stack Developer
          </button>
        </div>
      </div>
    </main>
  );
}
