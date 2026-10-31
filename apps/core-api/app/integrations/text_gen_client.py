"""Meta Muse text generation client for Core API.

CLAUDE.md restricts AI calls to the turn resolution service, but a ruler
backstory draft is a short, synchronous, user-initiated authoring action with no
relation to the turn pipeline. This is an approved exception of the same kind as
image_gen_client.py. The only file permitted to call this module is
app/services/ruler_backstory_service.py.
"""

from __future__ import annotations

import httpx
import structlog
from app.config import settings
from app.exceptions.text_generation_exceptions import TextGenerationError

logger = structlog.get_logger()

# NOTE: only ever log call metadata here (model, status, prompt length), never the prompt.
EVENT_TEXT_GENERATION_STARTED = "text_generation_started"
EVENT_TEXT_GENERATION_ERROR = "text_generation_error"

REASONING_HEADROOM_TOKENS = 1024
_FINISH_REASON_STOP = "stop"


def _extract_text(body: dict[str, object]) -> str:
    choices = body.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if choice.get("finish_reason") != _FINISH_REASON_STOP or not isinstance(
        content, str
    ):
        raise TextGenerationError("Text generation returned no usable text")
    text = content.strip()
    if not text:
        raise TextGenerationError("Text generation returned no usable text")
    return text


async def generate_text(
    prompt: str, max_output_tokens: int, timeout_seconds: int
) -> str:
    """Generate plain text from a single prompt with Muse Spark."""
    logger.info(
        EVENT_TEXT_GENERATION_STARTED,
        model=settings.muse_text_model_name,
        prompt_length=len(prompt),
    )
    payload = {
        "model": settings.muse_text_model_name,
        "reasoning_effort": settings.muse_text_reasoning_effort,
        "max_completion_tokens": max_output_tokens + REASONING_HEADROOM_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Authorization": f"Bearer {settings.muse_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as http_client:
            response = await http_client.post(
                f"{settings.muse_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            EVENT_TEXT_GENERATION_ERROR, status_code=exc.response.status_code
        )
        raise TextGenerationError() from exc
    except httpx.TransportError as exc:
        logger.warning(EVENT_TEXT_GENERATION_ERROR, error_type=type(exc).__name__)
        raise TextGenerationError() from exc
    return _extract_text(response.json())
