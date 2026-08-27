from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.health import router as health_router
from src.api.routes.recommendation import router as recommendation_router
from src.api.routes.auth import router as auth_router
from src.api.routes.profile import router as profile_router
from src.api.routes.skills import router as skills_router
from src.api.routes.mentor import router as mentor_router


app = FastAPI(
    title="Personalized Learning Path Recommender API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(skills_router)
app.include_router(recommendation_router)
app.include_router(mentor_router)