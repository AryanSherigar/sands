"""Meta Muse image generation client for Turn Resolution Service.

CLAUDE.md restricts AI calls to this service. The equivalent client in Core
API (Studio cover and portrait generation) is an intentional, approved
exception documented there. Only app/turn/steps/scene_image_generator.py
(in-turn scene images) and app/turn/steps/strategy_art_generator.py (strategy
event and chronicle art) may call this module.
"""

from __future__ import annotations

import base64
import binascii

import httpx
import structlog
from app.config import settings
from app.exceptions.turn_exceptions import SceneImageGenerationError

logger = structlog.get_logger()

# NOTE: only ever log image generation call metadata here (model, duration,
# prompt length) — never the prompt text itself, per the redaction policy
# openai_compatible_client.py documents for narration.
EVENT_IMAGE_GENERATION_STARTED = "scene_image_generation_started"
EVENT_IMAGE_GENERATION_ERROR = "scene_image_generation_error"

_OUTPUT_FORMAT = "webp"
_CONTENT_TYPE = "image/webp"
_EXTENSION = ".webp"


def output_content_type() -> str:
    """Content type of the bytes `generate_image` returns."""
    return _CONTENT_TYPE


def output_extension() -> str:
    return _EXTENSION


async def generate_image(prompt: str, timeout_seconds: int) -> bytes:
    """Generate a single image from a text prompt with Meta Muse Image."""
    logger.info(
        EVENT_IMAGE_GENERATION_STARTED,
        model=settings.muse_image_model_name,
        prompt_length=len(prompt),
    )
    payload = {
        "model": settings.muse_image_model_name,
        "prompt": prompt,
        "n": 1,
        "output_format": _OUTPUT_FORMAT,
        "reasoning_strength": settings.muse_image_reasoning_strength,
        "response_format": "b64_json",
    }
    headers = {"Authorization": f"Bearer {settings.muse_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as http_client:
            response = await http_client.post(
                f"{settings.muse_base_url}/images/generations",
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            EVENT_IMAGE_GENERATION_ERROR, status_code=exc.response.status_code
        )
        raise SceneImageGenerationError() from exc
    except httpx.TransportError as exc:
        logger.warning(EVENT_IMAGE_GENERATION_ERROR, error_type=type(exc).__name__)
        raise SceneImageGenerationError() from exc
    return _decode_image(response.json())


def _decode_image(body: dict[str, object]) -> bytes:
    items = body.get("data")
    first = items[0] if isinstance(items, list) and items else None
    encoded = first.get("b64_json") if isinstance(first, dict) else None
    if not isinstance(encoded, str) or not encoded:
        raise SceneImageGenerationError("Image generation returned no image bytes")
    try:
        return base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise SceneImageGenerationError("Image generation returned bad data") from exc
