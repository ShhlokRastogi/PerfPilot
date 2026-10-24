import os
from typing import Optional, List
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from backend.app.core.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])

class LLMConfigResponse(BaseModel):
    active_model: str
    fallback_model: str
    mock_mode: bool
    has_groq_key: bool
    has_openai_key: bool
    has_anthropic_key: bool
    has_gemini_key: bool
    available_models: List[str]

class UpdateLLMConfigRequest(BaseModel):
    model: Optional[str] = Field(default=None, description="Primary LLM Model (e.g. groq/llama-3.1-8b-instant)")
    fallback_model: Optional[str] = None
    mock_mode: Optional[bool] = None

@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config():
    """
    Returns current LLM runtime configuration. Never exposes raw credentials to the client.
    """
    has_groq = bool(settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY"))
    has_openai = bool(settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY"))
    has_gemini = bool(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"))

    available = [
        "groq/openai/gpt-oss-120b",
        "groq/qwen/qwen3.8-27b",
        "groq/llama-3.1-8b-instant",
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "groq/mixtral-8x7b-32768",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
    ]

    return LLMConfigResponse(
        active_model=settings.LITELLM_MODEL,
        fallback_model=settings.LITELLM_FALLBACK_MODEL,
        mock_mode=settings.MOCK_LLM,
        has_groq_key=has_groq,
        has_openai_key=has_openai,
        has_anthropic_key=has_anthropic,
        has_gemini_key=has_gemini,
        available_models=available,
    )

@router.post("/llm", response_model=LLMConfigResponse)
async def update_llm_config(req: UpdateLLMConfigRequest):
    """
    Updates active model selections at runtime.
    API keys remain securely managed on the backend server environment only.
    """
    if req.model:
        settings.LITELLM_MODEL = req.model.strip()

    if req.fallback_model:
        settings.LITELLM_FALLBACK_MODEL = req.fallback_model.strip()

    if req.mock_mode is not None:
        settings.MOCK_LLM = req.mock_mode

    return await get_llm_config()
