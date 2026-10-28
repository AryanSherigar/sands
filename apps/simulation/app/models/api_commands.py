from typing import Literal

from app.models.base import WorldModel
from app.models.battle_command import AcceptedCommand, Command
from app.models.battle_progress import OperationGuard
from pydantic import Field


class AcceptCommandRequest(OperationGuard):
    command: Command


class EconomyChoiceRequest(OperationGuard):
    choice: Literal["shortfall_take_loan", "shortfall_default"]


class CommandPage(WorldModel):
    items: list[AcceptedCommand] = Field(default_factory=list)
    next_after_id: str | None = None
