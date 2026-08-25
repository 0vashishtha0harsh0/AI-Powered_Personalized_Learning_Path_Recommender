from fastapi import HTTPException

from src.api.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RoadmapItem,
    TargetCareer,
)


def build_recommendation_response(
    occupation,
    roadmap_df,
) -> RecommendationResponse:
    """
    Convert recommendation engine output into
    the API response format.

    The recommendation engine returns:
        - occupation: pandas Series
        - roadmap_df: pandas DataFrame

    FastAPI should return:
        - RecommendationResponse
    """

    target_career = TargetCareer(
        onet_soc_code=str(
            occupation["onet_soc_code"]
        ),
        title=str(
            occupation["title"]
        ),
        similarity=float(
            occupation["similarity"]
        ),
    )

    roadmap = []

    for _, row in roadmap_df.iterrows():

        roadmap.append(
            RoadmapItem(
                milestone=int(
                    row["milestone"]
                ),
                skill_label=str(
                    row["skill_label"]
                ),
                gap_weight=float(
                    row["gap_weight"]
                ),
                course_title=str(
                    row["course_title"]
                ),
                course_source=str(
                    row["course_source"]
                ),
                course_difficulty=str(
                    row["course_difficulty"]
                ),
                course_url=str(
                    row["course_url"]
                ),
                explanation=str(
                    row["explanation"]
                ),
            )
        )

    return RecommendationResponse(
        target_career=target_career,
        roadmap=roadmap,
    )


def generate_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    """
    Generate a personalized learning recommendation.

    The recommendation engine will be connected here
    once the data pipeline is ready.
    """

    raise HTTPException(
        status_code=503,
        detail="Recommendation engine is not connected yet.",
    )