const email = localStorage.getItem("pathai.email") || "anonymous";
const savedRecommendation = (() => {
  try {
    const raw = localStorage.getItem(`pathai.recommendation.v3.${email}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
})();

const savedSkills = (() => {
  try {
    return JSON.parse(localStorage.getItem(`pathai.skills.${email}`) || "[]");
  } catch {
    return [];
  }
})();
const savedGoal = localStorage.getItem(`pathai.goal.${email}`) || "";
const savedSkillLevels = (() => {
  try { return JSON.parse(localStorage.getItem(`pathai.skillLevels.${email}`) || "[]"); } catch { return []; }
})();
const savedMilestones = savedRecommendation?.roadmap?.length || 0;
const completedMilestones = (() => {
  try { return JSON.parse(localStorage.getItem(`pathai.completedMilestones.${email}`) || "[]"); } catch { return []; }
})();

export type LearningPathItem = {
  title: string;
  status: string;
  type: string;
  time: string;
  explanation?: string;
  progress?: number;
  courseUrl?: string;
  courses?: Array<{ title: string; source: string; url: string; score: number }>;
};

export const learner = {
  name: email.split("@")[0] || "Learner",
  goal: savedGoal || savedRecommendation?.target_career?.title || "Set your learning goal",
  progress: savedMilestones ? Math.round((completedMilestones.length / savedMilestones) * 100) : 0,
  streak: 0,
  hours: 0,
  milestones: savedRecommendation?.roadmap?.length || 0,
  level: "Intermediate",
  style: "Hands-on · Project-based"
};

const levelScore: Record<string, number> = { Beginner: 30, Intermediate: 60, Advanced: 85 };
export const skills: Array<[string, number]> = savedSkills.map((skill: string) => {
  const selected = savedSkillLevels.find((item: any) => item.label === skill);
  return [skill, levelScore[selected?.level] || 60];
});

export const skillGaps: Array<[string, number]> = (savedRecommendation?.roadmap || []).map((item: any) => [
  item.skill_label,
  Math.max(1, Math.round((1 - Number(item.gap_weight || 0)) * 100)),
]);

if (savedRecommendation?.skill_gaps?.length) {
  skillGaps.splice(0, skillGaps.length, ...savedRecommendation.skill_gaps.map((item: any) => [
    item.skill,
    Math.min(100, Math.round(Number(item.gap_score || 0) * 100)),
  ]));
}

export const path: LearningPathItem[] = (savedRecommendation?.roadmap || []).map((item: any, index: number) => ({
  title: item.course_title || item.skill_label,
  status: index === 0 ? "current" : "locked",
  type: item.skill_label,
  time: item.course_difficulty || "Self-paced",
  explanation: item.explanation,
  courseUrl: item.course_url,
  courses: item.recommended_courses,
  progress: savedMilestones ? Math.round((completedMilestones.length / savedMilestones) * 100) : 0,
}));

export const recommendations = (savedRecommendation?.roadmap || []).slice(0, 3).map((item: any) => ({
  title: item.course_title || item.skill_label,
  score: Math.round(Number(item.gap_weight || 0) * 100),
  time: item.course_difficulty || "Self-paced",
  level: item.course_source || "Recommended",
  reason: item.explanation || `Builds the ${item.skill_label} gap for your target career.`,
}));

export const weekly = [
  { day: "M", hours: 0 }, { day: "T", hours: 0 }, { day: "W", hours: 0 },
  { day: "T", hours: 0 }, { day: "F", hours: 0 }, { day: "S", hours: 0 }, { day: "S", hours: 0 }
];
