from fastapi import FastAPI

from src.api.routes.health import router as health_router
from src.api.routes.recommendation import router as recommendation_router


app = FastAPI(
    title="Personalized Learning Path Recommender API",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(recommendation_router)