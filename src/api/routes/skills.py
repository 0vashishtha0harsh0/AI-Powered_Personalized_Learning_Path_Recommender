from fastapi import APIRouter, Depends

from src.api.routes.auth import current_user
from src.api.schemas.auth import User
from src.api.services.recommendation_service import list_skills

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get("")
def get_skills(_user: User = Depends(current_user)):
    return list_skills()