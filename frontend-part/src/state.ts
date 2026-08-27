const accountKey = () => localStorage.getItem("pathai.email") || "anonymous";
const PROGRESS_KEY = () => `pathai.completedMilestones.${accountKey()}`;
const PROFILE_KEY = () => `pathai.profile.${accountKey()}`;

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
}