const accountKey = () => localStorage.getItem("pathai.email") || "anonymous";
const PROGRESS_KEY = () => `pathai.completedMilestones.${accountKey()}`;
const PROFILE_KEY = () => `pathai.profile.${accountKey()}`;
export const PATHAI_STATE_CHANGED = "pathai-state-changed";

export function notifyPathAIStateChanged() {
  window.dispatchEvent(new Event(PATHAI_STATE_CHANGED));
}

export function getCompletedMilestones(): number[] {
  try {
    return JSON.parse(localStorage.getItem(PROGRESS_KEY()) || "[]");
  } catch {
    return [];
  }
}

export function completeMilestone(milestone: number) {
  const completed = getCompletedMilestones();
  if (!completed.includes(milestone)) {
    localStorage.setItem(PROGRESS_KEY(), JSON.stringify([...completed, milestone]));
    notifyPathAIStateChanged();
  }
}

export function getProfile() {
  try {
    return JSON.parse(localStorage.getItem(PROFILE_KEY()) || "{}");
  } catch {
    return {};
  }
}

export function saveProfile(profile: { name: string; level: string; style: string }) {
  localStorage.setItem(PROFILE_KEY(), JSON.stringify(profile));
  notifyPathAIStateChanged();
}

export function accountEmail() {
  return accountKey();
}

export function getStoredRecommendation() {
  try {
    const raw = localStorage.getItem(`pathai.recommendation.v3.${accountKey()}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredGoal() {
  return localStorage.getItem(`pathai.goal.${accountKey()}`) || "";
}

export function getStoredSkills(): string[] {
  try {
    return JSON.parse(localStorage.getItem(`pathai.skills.${accountKey()}`) || "[]");
  } catch {
    return [];
  }
}

export function getStoredSkillLevels(): Array<{ label: string; level: string }> {
  try {
    return JSON.parse(localStorage.getItem(`pathai.skillLevels.${accountKey()}`) || "[]");
  } catch {
    return [];
  }
}
