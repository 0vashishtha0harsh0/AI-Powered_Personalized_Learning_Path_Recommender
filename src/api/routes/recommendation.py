from fastapi import APIRouter, Depends

from src.api.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from src.api.services.recommendation_service import (
    generate_recommendation,
)
from src.api.routes.auth import current_user


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


@router.post(
    "",
    response_model=RecommendationResponse,
)
def create_recommendation(
    request: RecommendationRequest,
    _user=Depends(current_user),
):
    return generate_recommendation(request)