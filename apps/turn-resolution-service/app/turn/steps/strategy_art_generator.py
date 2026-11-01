"""Generates event, uprising and chronicle art for strategy mode.

A missing image must never fail or degrade a turn: this module never raises
into its caller. Prompts carry only the allowlisted briefing fields, each
quoted and length-bounded, never player free text.
"""

import uuid

import structlog
from app.exceptions.turn_exceptions import SceneImageGenerationError
from app.integrations import image_gen_client, storage_client
from strategy_contracts.art import ArtBriefing

logger = structlog.get_logger()

EVENT_STRATEGY_ART_FAILED = "strategy_art_generation_failed"
MAX_PROMPT_FIELD_CHARS = 160
ART_OBJECT_PREFIX = "strategy-art"
_STYLE = (
    "Hand-painted manuscript illumination in a muted watercolor palette on warm "
    "parchment, a single dramatic scene from a medieval realm."
)
_NO_TEXT_INSTRUCTION = "No text or lettering in the image."


def _bounded(value: str) -> str:
    return value[:MAX_PROMPT_FIELD_CHARS]


def build_art_prompt(briefing: ArtBriefing) -> str:
    parts = [_STYLE, f'Scene (quoted data): "{_bounded(briefing.headline)}".']
    if briefing.subject_name:
        parts.append(
            f'Place or person (quoted data): "{_bounded(briefing.subject_name)}".'
        )
    causes = [_bounded(key.replace("_", " ")) for key in briefing.cause_keys]
    if causes:
        parts.append("Circumstances: " + ", ".join(causes) + ".")
    parts.append(_NO_TEXT_INSTRUCTION)
    return " ".join(parts)


async def generate_strategy_art(
    briefing: ArtBriefing, timeout_seconds: int
) -> str | None:
    """Generate and upload art; returns the public URL, or None on any failure."""
    prompt = build_art_prompt(briefing)
    try:
        image_bytes = await image_gen_client.generate_image(prompt, timeout_seconds)
        object_key = (
            f"{ART_OBJECT_PREFIX}/{uuid.uuid4()}{image_gen_client.output_extension()}"
        )
        return await storage_client.upload_image(
            image_bytes, image_gen_client.output_content_type(), object_key
        )
    except SceneImageGenerationError:
        logger.warning(EVENT_STRATEGY_ART_FAILED, kind=briefing.kind, exc_info=True)
        return None
