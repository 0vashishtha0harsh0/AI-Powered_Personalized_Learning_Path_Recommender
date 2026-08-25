from fastapi import APIRouter

from src.api.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from src.api.services.recommendation_service import (
    generate_recommendation,
)


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
):
    return generate_recommendation(request)