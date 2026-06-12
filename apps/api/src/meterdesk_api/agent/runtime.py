from __future__ import annotations

from fastapi import HTTPException

from meterdesk_api.agent.provider import AgentResolutionProvider, OpenAICompatibleProvider
from meterdesk_api.eval.judge import EvalDraftJudge, OpenAICompatibleEvalJudge
from meterdesk_api.settings import get_settings


async def get_agent_provider() -> AgentResolutionProvider:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_model:
        raise HTTPException(
            status_code=503,
            detail="OpenAI-compatible provider is not configured",
        )
    return OpenAICompatibleProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
    )


async def get_optional_agent_provider() -> AgentResolutionProvider | None:
    try:
        return await get_agent_provider()
    except HTTPException as error:
        if error.status_code == 503:
            return None
        raise


async def get_optional_eval_judge() -> EvalDraftJudge | None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_model:
        return None
    return OpenAICompatibleEvalJudge(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
    )
