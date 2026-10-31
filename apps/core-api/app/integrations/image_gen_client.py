"""Meta Muse image generation client for Core API.

CLAUDE.md restricts AI calls to the turn resolution service, but cover
image generation is a Studio-only, synchronous, user-initiated action with
no relation to the turn pipeline — routing it through TRS would add a
needless service hop. Core API and TRS therefore each own an independent
image_gen_client.py; this is an intentional, approved exception, not an
oversight. The only files permitted to call this module are
app/services/upload_service.py and app/services/map_generation_service.py.
"""

from __future__ import annotations

import base64
import binascii

import httpx
import structlog
from app.config import settings
from app.exceptions.upload_exceptions import ImageGenerationError

logger = structlog.get_logger()

# NOTE: only ever log image generation call metadata here (model, duration,
# prompt length) — never the prompt text itself, per the redaction policy
# the narration client documents in TRS.
EVENT_IMAGE_GENERATION_STARTED = "image_generation_started"
EVENT_IMAGE_GENERATION_ERROR = "image_generation_error"

_OUTPUT_FORMAT = "webp"
_CONTENT_TYPE = "image/webp"
_EXTENSION = ".webp"


def output_content_type() -> str:
    """Content type of the bytes `generate_image` returns."""
    return _CONTENT_TYPE


def output_extension() -> str:
    return _EXTENSION


async def generate_image(
    prompt: str, timeout_seconds: int, size: str | None = None
) -> bytes:
    """Generate a single image from a text prompt with Meta Muse Image."""
    logger.info(
        EVENT_IMAGE_GENERATION_STARTED,
        model=settings.muse_image_model_name,
        prompt_length=len(prompt),
    )
    payload = _base_payload(prompt)
    if size is not None:
        payload["size"] = size
    return await _post_image_request("/images/generations", payload, timeout_seconds)


async def edit_image(
    prompt: str, image_bytes: bytes, content_type: str, timeout_seconds: int
) -> bytes:
    """Repaint a source image from a text prompt with Meta Muse Image."""
    logger.info(
        EVENT_IMAGE_GENERATION_STARTED,
        model=settings.muse_image_model_name,
        prompt_length=len(prompt),
        source_bytes=len(image_bytes),
    )
    encoded = base64.b64encode(image_bytes).decode()
    payload = _base_payload(prompt)
    payload["images"] = [{"image_url": f"data:{content_type};base64,{encoded}"}]
    return await _post_image_request("/images/edits", payload, timeout_seconds)


def _base_payload(prompt: str) -> dict[str, object]:
    return {
        "model": settings.muse_image_model_name,
        "prompt": prompt,
        "n": 1,
        "output_format": _OUTPUT_FORMAT,
        "reasoning_strength": settings.muse_image_reasoning_strength,
        "response_format": "b64_json",
    }


async def _post_image_request(
    path: str, payload: dict[str, object], timeout_seconds: int
) -> bytes:
    headers = {"Authorization": f"Bearer {settings.muse_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as http_client:
            response = await http_client.post(
                f"{settings.muse_base_url}{path}", json=payload, headers=headers
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            EVENT_IMAGE_GENERATION_ERROR, status_code=exc.response.status_code
        )
        raise ImageGenerationError() from exc
    except httpx.TransportError as exc:
        logger.warning(EVENT_IMAGE_GENERATION_ERROR, error_type=type(exc).__name__)
        raise ImageGenerationError() from exc
    return _decode_image(response.json())


def _decode_image(body: dict[str, object]) -> bytes:
    items = body.get("data")
    first = items[0] if isinstance(items, list) and items else None
    encoded = first.get("b64_json") if isinstance(first, dict) else None
    if not isinstance(encoded, str) or not encoded:
        raise ImageGenerationError("Image generation returned no image bytes")
    try:
        return base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ImageGenerationError("Image generation returned bad data") from exc
