from fastapi import APIRouter, Depends

from src.api.schemas.mentor import MentorChatRequest, MentorChatResponse
from src.api.services.mentor_service import chat_with_mentor, _get_provider, _get_model
from src.api.services.gemini_key_manager import get_key_manager
from src.api.routes.auth import current_user


router = APIRouter(prefix="/mentor", tags=["AI Mentor"])


@router.post("/chat", response_model=MentorChatResponse)
async def mentor_chat(
    request: MentorChatRequest,
    _user=Depends(current_user),
):
    """Chat with the AI Mentor using an LLM."""
    answer = await chat_with_mentor(
        question=request.question,
        conversation_history=request.conversation_history,
        recommendation_context=request.recommendation_context,
    )
    provider = _get_provider() or "none"
    model = _get_model(provider) if provider != "none" else "none"
    return MentorChatResponse(answer=answer, provider=f"{provider}/{model}")


@router.get("/status")
def mentor_status():
    """Check if AI Mentor is configured and available."""
    provider = _get_provider()
    model = _get_model(provider) if provider else "none"
    key_status = get_key_manager().get_status()
    return {
        "configured": provider is not None,
        "provider": provider or "none",
        "model": model,
        "key_pool": key_status,
    }


@router.get("/keys")
def key_status():
    """Return the Gemini key pool status (admin endpoint)."""
    return get_key_manager().get_status()
