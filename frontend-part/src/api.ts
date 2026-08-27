import { notifyPathAIStateChanged } from "./state";

export type Recommendation = {
  goal: string;
  current_skills: string[];
  target_career: {
    onet_soc_code: string;
    title: string;
    similarity: number;
    confidence: number;
  };
  skill_gaps: Array<{ skill_id: string; skill: string; gap_score: number; priority: string; reason: string }>;
  technologies: Array<{ name: string; demand_score: number; relevance_score: number }>;
  roadmap: Array<{
    milestone: number;
    skill_label: string;
    gap_weight: number;
    course_title: string;
    course_source: string;
    course_difficulty: string;
    course_url: string;
    explanation: string;
    recommended_courses: Array<{ title: string; source: string; difficulty: string; url: string; score: number }>;
    prerequisites: string[];
  }>;
};

export const API_URL = import.meta.env.VITE_API_URL || "https://ai-powered-personalized-learning-path-8bvq.onrender.com";

async function readError(response: Response, fallback: string) {
  const body = await response.json().catch(() => ({}));
  if (response.status === 401) {
    clearSession();
    return "Your session expired. Please sign in again.";
  }
  const detail = body.detail || body.message;
  return detail ? `${fallback} ${detail}` : `${fallback} Server returned ${response.status}.`;
}

export function getToken() {
  return localStorage.getItem("pathai.token");
}

export function clearSession() {
  localStorage.removeItem("pathai.token");
  localStorage.removeItem("pathai.email");
}

export async function authenticate(email: string, password: string, register: boolean) {
  const response = await fetch(`${API_URL}/auth/${register ? "register" : "login"}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Authentication failed.");
  localStorage.setItem("pathai.token", body.token);
  localStorage.setItem("pathai.email", body.email);
}

export async function createRecommendation(
  goal: string,
  currentSkills: string[] = [],
): Promise<Recommendation> {
  const response = await fetch(`${API_URL}/recommendations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken() || ""}`,
    },
    body: JSON.stringify({ goal, current_skills: currentSkills }),
  });

  if (!response.ok) {
    throw new Error(await readError(response, "Could not build your learning path."));
  }

  return response.json();
}

export function saveRecommendation(recommendation: Recommendation) {
  const email = localStorage.getItem("pathai.email") || "anonymous";
  localStorage.setItem(`pathai.recommendation.v3.${email}`, JSON.stringify(recommendation));
  notifyPathAIStateChanged();
}

export async function saveLearnerProfile(goal: string, currentSkills: string[]) {
  const response = await fetch(`${API_URL}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() || ""}` },
    body: JSON.stringify({ goal, current_skills: currentSkills, level: "Intermediate", learning_style: "Hands-on" }),
  });
  if (!response.ok) throw new Error(await readError(response, "Could not save your learner profile."));
}

export async function getSkills(): Promise<Array<{ id: string; label: string }>> {
  const response = await fetch(`${API_URL}/skills`, {
    headers: { Authorization: `Bearer ${getToken() || ""}` },
  });
  if (!response.ok) throw new Error(await readError(response, "Could not load the skill catalogue."));
  return response.json();
}
