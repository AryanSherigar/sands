"""Pydantic shapes for the Studio lore box: free text plus linked answer blocks."""

from typing import Literal

from pydantic import BaseModel, Field

MAX_LORE_BLOCKS = 200
MAX_LORE_BLOCK_TEXT_LENGTH = 20000
MAX_LORE_LABEL_LENGTH = 120


class LoreBlock(BaseModel):
    """One ordered block of a lore document."""

    kind: Literal["text", "answer"]
    question_id: str | None = Field(default=None, max_length=MAX_LORE_LABEL_LENGTH)
    label: str | None = Field(default=None, max_length=MAX_LORE_LABEL_LENGTH)
    text: str = Field(default="", max_length=MAX_LORE_BLOCK_TEXT_LENGTH)


class LoreDocument(BaseModel):
    """The ordered blocks behind one lore box."""

    blocks: list[LoreBlock] = Field(default_factory=list, max_length=MAX_LORE_BLOCKS)
