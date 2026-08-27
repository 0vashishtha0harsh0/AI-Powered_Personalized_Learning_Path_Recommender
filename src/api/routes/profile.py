import json

from fastapi import APIRouter, Depends

from src.api.routes.auth import current_user
from src.api.schemas.auth import LearnerProfile, User
from src.api.services.auth_service import _connection

router = APIRouter(prefix="/profile", tags=["Learner Profile"])


@router.get("", response_model=LearnerProfile)
def read_profile(user: User = Depends(current_user)):
    connection = _connection()
    try:
        row = connection.execute(
            "SELECT goal, current_skills, level, learning_style FROM learner_profiles WHERE user_id = ?",
            (user.id,),
        ).fetchone()
        if not row:
            return LearnerProfile(goal="", current_skills=[])
        return LearnerProfile(goal=row["goal"], current_skills=json.loads(row["current_skills"]), level=row["level"], learning_style=row["learning_style"])
    finally:
        connection.close()


@router.put("", response_model=LearnerProfile)
def update_profile(profile: LearnerProfile, user: User = Depends(current_user)):
    from src.api.services.auth_service import save_profile
    return save_profile(user.id, profile.model_dump())