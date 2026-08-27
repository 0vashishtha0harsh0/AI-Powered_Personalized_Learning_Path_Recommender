import {
  accountEmail,
  getCompletedMilestones,
  getProfile,
  getStoredGoal,
  getStoredRecommendation,
  getStoredSkillLevels,
  getStoredSkills,
} from "../state";

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

const levelScore: Record<string, number> = { Beginner: 30, Intermediate: 60, Advanced: 85 };

export function getLearningData() {
  const email = accountEmail();
  const savedRecommendation = getStoredRecommendation();
  const savedSkills = getStoredSkills();
  const savedSkillLevels = getStoredSkillLevels();
  const savedGoal = getStoredGoal();
  const completedMilestones = getCompletedMilestones();
  const savedProfile = getProfile();
  const milestones = savedRecommendation?.roadmap?.length || 0;
  const completion = milestones ? Math.round((completedMilestones.length / milestones) * 100) : 0;

  const learner = {
    name: savedProfile.name || email.split("@")[0] || "Learner",
    goal: savedGoal || savedRecommendation?.target_career?.title || "Set your learning goal",
    progress: completion,
    streak: 0,
    hours: 0,
    milestones,
    level: savedProfile.level || "Intermediate",
    style: savedProfile.style || "Hands-on · Project-based",
  };

  const skills: Array<[string, number]> = savedSkills.map((skill: string) => {
    const selected = savedSkillLevels.find((item: any) => item.label === skill);
    const level = selected?.level || "Intermediate";
    return [skill, levelScore[level] || 60];
  });

  const skillGaps: Array<[string, number]> = (savedRecommendation?.roadmap || []).map((item: any) => [
    item.skill_label,
    Math.max(1, Math.round((1 - Number(item.gap_weight || 0)) * 100)),
  ]);

  if (savedRecommendation?.skill_gaps?.length) {
    skillGaps.splice(0, skillGaps.length, ...savedRecommendation.skill_gaps.map((item: any) => [
      item.skill,
      Math.min(100, Math.round(Number(item.gap_score || 0) * 100)),
    ]));
  }

  const path: LearningPathItem[] = (savedRecommendation?.roadmap || []).map((item: any, index: number) => ({
    title: item.course_title || item.skill_label,
    status: index === completedMilestones.length ? "current" : "locked",
    type: item.skill_label,
    time: item.course_difficulty || "Self-paced",
    explanation: item.explanation,
    courseUrl: item.course_url,
    courses: item.recommended_courses,
    progress: completion,
  }));

  const recommendations = (savedRecommendation?.roadmap || []).slice(completedMilestones.length, completedMilestones.length + 3).map((item: any) => ({
    title: item.course_title || item.skill_label,
    score: Math.round(Number(item.gap_weight || 0) * 100),
    time: item.course_difficulty || "Self-paced",
    level: item.course_source || "Recommended",
    reason: item.explanation || `Builds the ${item.skill_label} gap for your target career.`,
  }));

  return {
    learner,
    skills,
    skillGaps,
    path,
    recommendations,
    completion,
    completedMilestones,
    recommendation: savedRecommendation,
  };
}

const current = getLearningData();

export const learner = current.learner;
export const skills = current.skills;
export const skillGaps = current.skillGaps;
export const path = current.path;
export const recommendations = current.recommendations;
export const weekly = [
  { day: "M", hours: 0 }, { day: "T", hours: 0 }, { day: "W", hours: 0 },
  { day: "T", hours: 0 }, { day: "F", hours: 0 }, { day: "S", hours: 0 }, { day: "S", hours: 0 }
];
