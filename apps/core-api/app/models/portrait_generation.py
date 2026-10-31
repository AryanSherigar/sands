"""Pydantic models for leader portrait generation."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

MIN_PORTRAIT_PROMPT_CHARS = 1
MAX_PORTRAIT_PROMPT_CHARS = 1000

PortraitPrompt = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=MIN_PORTRAIT_PROMPT_CHARS,
        max_length=MAX_PORTRAIT_PROMPT_CHARS,
    ),
]


class PortraitGenerationRequest(BaseModel):
    prompt: PortraitPrompt


class GeneratedPortrait(BaseModel):
    image_url: str
