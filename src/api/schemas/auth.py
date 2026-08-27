from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    token: str
    email: str


class User(BaseModel):
    id: int
    email: str


class LearnerProfile(BaseModel):
    goal: str = ""
    current_skills: list[str] = Field(default_factory=list)
    level: str = "Intermediate"
    learning_style: str = "Hands-on"