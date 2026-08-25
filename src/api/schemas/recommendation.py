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


class TargetCareer(BaseModel):
    onet_soc_code: str
    title: str
    similarity: float


class RoadmapItem(BaseModel):
    milestone: int
    skill_label: str
    gap_weight: float
    course_title: str
    course_source: str
    course_difficulty: str
    course_url: str
    explanation: str


class RecommendationResponse(BaseModel):
    target_career: TargetCareer
    roadmap: list[RoadmapItem]