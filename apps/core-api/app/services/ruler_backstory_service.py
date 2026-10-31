"""Drafts a coronation chronicle entry for a customized strategy ruler."""

from app.config import settings
from app.integrations import text_gen_client
from app.models.strategy_ruler import RulerBackstoryRequest

BACKSTORY_MAX_OUTPUT_TOKENS = 180
_DEFAULT_TRAIT = "steadfast"
_DEFAULT_AMBITION = "prosperity"


def build_backstory_prompt(req: RulerBackstoryRequest) -> str:
    traits = ", ".join(req.trait_ids) or _DEFAULT_TRAIT
    ambitions = ", ".join(req.ambition_ids) or _DEFAULT_AMBITION
    epithet_part = f", {req.epithet}" if req.epithet else ""
    return (
        "You are a medieval court chronicler. Write a concise 2-3 sentence evocative "
        f"coronation chronicle entry for {req.ruler_name}{epithet_part} of {req.faction_id}. "
        f"Incorporate their virtues: {traits} and ambition: {ambitions}. "
        "Style: ancient, atmospheric, poetic parchment tone without modern clichés."
    )


async def generate_ruler_backstory(req: RulerBackstoryRequest) -> str:
    """Generate 2-3 sentences of atmospheric coronation chronicle prose."""
    return await text_gen_client.generate_text(
        build_backstory_prompt(req),
        BACKSTORY_MAX_OUTPUT_TOKENS,
        settings.text_generation_timeout_seconds,
    )
