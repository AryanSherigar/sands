"""Pydantic request and response schemas for sheet rules (tool `rule_sheet`)."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RULE_STATUSES = ("unrevealed", "intact", "active_threat", "violated", "corrupted")
INITIAL_STATUSES = ("unrevealed", "intact")
SOURCE_STYLES = ("typed", "pencil", "ink", "printed", "spoken", "ink_block")
SHEET_RULE_KEY_PATTERN = r"^[a-z][a-z0-9_]{0,30}$"
MAX_RULE_TEXT_LENGTH = 600
MAX_RULE_NUMBER = 99

InitialStatus = Literal["unrevealed", "intact"]
SourceStyle = Literal["typed", "pencil", "ink", "printed", "spoken", "ink_block"]


class SheetRuleCreate(BaseModel):
    """Payload to add a rule to a master-mode scenario's clipboard."""

    key: str = Field(pattern=SHEET_RULE_KEY_PATTERN)
    number: int = Field(ge=1, le=MAX_RULE_NUMBER)
    text: str = Field(min_length=1, max_length=MAX_RULE_TEXT_LENGTH)
    corrupted_text: str | None = Field(default=None, max_length=MAX_RULE_TEXT_LENGTH)
    initial_status: InitialStatus = "intact"
    source_style: SourceStyle = "typed"
    is_ai_flaggable: bool = False
    display_order: int = 0


class SheetRuleUpdate(BaseModel):
    """Partial update; the key is the rule's identity in state and cannot change."""

    number: int | None = Field(default=None, ge=1, le=MAX_RULE_NUMBER)
    text: str | None = Field(
        default=None, min_length=1, max_length=MAX_RULE_TEXT_LENGTH
    )
    corrupted_text: str | None = Field(default=None, max_length=MAX_RULE_TEXT_LENGTH)
    initial_status: InitialStatus | None = None
    source_style: SourceStyle | None = None
    is_ai_flaggable: bool | None = None
    display_order: int | None = None


class SheetRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_id: uuid.UUID
    scenario_id: uuid.UUID
    key: str
    number: int
    text: str
    corrupted_text: str | None = None
    initial_status: str
    source_style: str
    is_ai_flaggable: bool
    display_order: int


class SheetRuleListResponse(BaseModel):
    items: list[SheetRuleResponse]


class SheetRuleReorderRequest(BaseModel):
    ordered_rule_ids: list[uuid.UUID]
