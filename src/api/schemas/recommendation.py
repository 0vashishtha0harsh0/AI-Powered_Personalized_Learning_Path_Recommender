from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    goal: str = Field(
        ...,
        min_length=1,
        description="The learner's career or learning goal",
    )

    current_skills: list[str] = Field(
        default_factory=list,
        description="Skills the learner already has",
    )

    learner_skill_ids: list[str] = Field(
        default_factory=list,
        description="Optional ESCO skill IDs already known by the learner",
    )


class SkillGap(BaseModel):
    skill_id: str
    skill: str
    gap_score: float
    priority: str
    reason: str


class TechnologyRecommendation(BaseModel):
    name: str
    demand_score: float
    relevance_score: float


class TargetCareer(BaseModel):
    onet_soc_code: str
    title: str
    similarity: float
    confidence: float = 0.0


class RoadmapItem(BaseModel):
    milestone: int
    skill_label: str
    gap_weight: float
    course_title: str
    course_source: str
    course_difficulty: str
    course_url: str = ""
    explanation: str
    recommended_courses: list[dict] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    goal: str
    current_skills: list[str]
    target_career: TargetCareer
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    technologies: list[TechnologyRecommendation] = Field(default_factory=list)
    roadmap: list[RoadmapItem]