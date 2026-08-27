import os
import httpx

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------
# Set your LLM provider key via environment variables:
#   GEMINI_API_KEY=AIza...          (Google Gemini — default)
#   OPENAI_API_KEY=sk-...           (OpenAI / OpenRouter — fallback)
#   ANTHROPIC_API_KEY=sk-ant-...    (Anthropic Claude — fallback)
#
# Override model:
#   LLM_MODEL=gemini-3.6-flash      (default)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DEFAULT_MODELS = {
    "gemini": "gemini-3.6-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}

MENTOR_SYSTEM_PROMPT = """You are PathAI Mentor — an expert AI learning coach inside the PathAI personalized learning platform.

You have access to the learner's profile and their current learning path. Use this context to give helpful, specific advice.

Core rules:
- Be conversational and encouraging but concise.
- Reference the learner's actual skill gaps, goals and roadmap when relevant.
- If the learner asks about a specific skill or course, explain why it matters for their goal.
- If they ask whether they can skip something, give an honest assessment of prerequisites.
- If they ask to test their knowledge, ask a targeted question based on their current milestone.
- Keep answers under 3-4 sentences unless they ask for detail.
- Never fabricate course URLs or specific statistics — say "I'd recommend checking the course page" instead.
- Use markdown formatting: **bold** for emphasis, bullet points for lists.
"""


def _get_provider():
    """Detect which LLM provider is configured. Gemini is preferred."""
    if GEMINI_API_KEY:
        return "gemini"
    if OPENAI_API_KEY:
        return "openai"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return None


def _get_model(provider: str) -> str:
    """Get the model name, respecting LLM_MODEL override."""
    return os.environ.get("LLM_MODEL", DEFAULT_MODELS.get(provider, "gemini-3.6-flash"))


def _build_user_message(question: str, context: dict) -> str:
    """Build a rich user message with learner context."""
    parts = [f"## Learner Question\n{question}\n"]

    if context.get("goal"):
        parts.append(f"## Learner Goal\n{context['goal']}")
    if context.get("target_career"):
        parts.append(f"## Target Career\n{context['target_career']}")
    if context.get("current_skills"):
        parts.append(f"## Current Skills\n{', '.join(context['current_skills'])}")
    if context.get("skill_gaps"):
        gaps = context["skill_gaps"][:8]
        parts.append("## Identified Skill Gaps\n" + "\n".join(
            f"- {g['skill']} (priority: {g.get('priority', 'medium')})"
            for g in gaps
        ))
    if context.get("roadmap"):
        roadmap = context["roadmap"][:6]
        parts.append("## Current Learning Roadmap\n" + "\n".join(
            f"- Milestone {r['milestone']}: {r['skill_label']} — {r['course_title']}"
            for r in roadmap
        ))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
async def _call_gemini(messages: list[dict]) -> str:
    """Call Google Gemini API (generativelanguage.googleapis.com)."""
    model = _get_model("gemini")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    # Convert OpenAI-style messages to Gemini format
    system_instruction = ""
    contents = []

    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        },
    }

    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            detail = response.text[:300]
            raise HTTPException(
                status_code=502,
                detail=f"Gemini API error ({response.status_code}): {detail}",
            )
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise HTTPException(
                status_code=502,
                detail="Gemini returned no candidates.",
            )
        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0]["text"] if parts else ""


# ---------------------------------------------------------------------------
# OpenAI (fallback)
# ---------------------------------------------------------------------------
async def _call_openai(messages: list[dict]) -> str:
    """Call OpenAI-compatible API."""
    model = _get_model("openai")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            detail = response.text[:300]
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI API error ({response.status_code}): {detail}",
            )
        data = response.json()
        return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Anthropic (fallback)
# ---------------------------------------------------------------------------
async def _call_anthropic(messages: list[dict]) -> str:
    """Call Anthropic Claude API."""
    model = _get_model("anthropic")
    system_msg = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            user_messages.append(msg)

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 800,
        "system": system_msg,
        "messages": user_messages,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            detail = response.text[:300]
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic API error ({response.status_code}): {detail}",
            )
        data = response.json()
        return data["content"][0]["text"]


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------
def _build_context_from_recommendation(recommendation: dict) -> dict:
    """Extract learner context from the stored recommendation."""
    context = {}
    if recommendation.get("goal"):
        context["goal"] = recommendation["goal"]
    if recommendation.get("target_career"):
        context["target_career"] = recommendation["target_career"].get("title", "")
    if recommendation.get("current_skills"):
        context["current_skills"] = recommendation["current_skills"]
    if recommendation.get("skill_gaps"):
        context["skill_gaps"] = [
            {"skill": g.get("skill", ""), "priority": g.get("priority", "medium")}
            for g in recommendation["skill_gaps"]
        ]
    if recommendation.get("roadmap"):
        context["roadmap"] = [
            {
                "milestone": r.get("milestone", 0),
                "skill_label": r.get("skill_label", ""),
                "course_title": r.get("course_title", ""),
            }
            for r in recommendation["roadmap"]
        ]
    return context


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def chat_with_mentor(
    question: str,
    conversation_history: list[dict] = None,
    recommendation_context: dict = None,
) -> str:
    """
    Send a message to the AI Mentor and get a response.
    """
    provider = _get_provider()
    if not provider:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Mentor is not configured. Set GEMINI_API_KEY "
                "environment variable to enable the AI Mentor."
            ),
        )

    context = {}
    if recommendation_context:
        context = _build_context_from_recommendation(recommendation_context)

    user_message = _build_user_message(question, context)

    messages = [{"role": "system", "content": MENTOR_SYSTEM_PROMPT}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    messages.append({"role": "user", "content": user_message})

    if provider == "gemini":
        return await _call_gemini(messages)
    elif provider == "anthropic":
        return await _call_anthropic(messages)
    else:
        return await _call_openai(messages)
