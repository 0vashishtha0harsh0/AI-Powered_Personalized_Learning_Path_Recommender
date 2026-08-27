from pydantic import BaseModel, Field


class MentorChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The learner's question for the AI Mentor",
    )
    conversation_history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages [{role, content}]",
    )
    recommendation_context: dict = Field(
        default_factory=dict,
        description="Learner's recommendation data for context-aware answers",
    )


class MentorChatResponse(BaseModel):
    answer: str
    provider: str
