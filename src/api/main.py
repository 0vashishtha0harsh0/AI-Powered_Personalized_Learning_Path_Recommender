from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.health import router as health_router
from src.api.routes.recommendation import router as recommendation_router
from src.api.routes.auth import router as auth_router
from src.api.routes.profile import router as profile_router
from src.api.routes.skills import router as skills_router
from src.api.routes.mentor import router as mentor_router
from src.api.services.gemini_key_manager import initialize_key_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize the Gemini key rotation pool
    await initialize_key_manager()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Personalized Learning Path Recommender API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-powered-personalized-learning-path-recommender-226dlmbfe.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
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
