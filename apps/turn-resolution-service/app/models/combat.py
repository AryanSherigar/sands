"""Public combat action and result shapes."""

from typing import Literal
from uuid import UUID

from app.combat.models import CombatAction, CombatEvent, CombatState, LegalAttack
from app.combat.resolver import legal_actions
from pydantic import BaseModel, ConfigDict, Field


class CombatActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    playthrough_id: UUID
    participant_id: UUID
    action: CombatAction


class CombatStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    playthrough_id: UUID
    participant_id: UUID
    client_action_id: UUID
    encounter_id: str = Field(min_length=1, max_length=128)


class CombatOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    playthrough_id: UUID
    participant_id: UUID
    client_action_id: UUID
    expected_revision: int = Field(strict=True, ge=0)


class CombatantView(BaseModel):
    actor_id: str
    side: Literal["player", "opponent"]
    health: int
    max_health: int


class CombatStateView(BaseModel):
    encounter_id: str
    revision: int
    round_number: int
    status: Literal["active", "player_defeated", "opponent_defeated"]
    current_actor_id: str | None
    outcome_id: str | None = None
    combatants: tuple[CombatantView, CombatantView]
    legal_actions: tuple[LegalAttack, ...]


class CombatActionResult(BaseModel):
    state: CombatStateView
    event: CombatEvent


class CombatOutcomeResult(BaseModel):
    state: CombatStateView
    outcome_id: str


class AvailableEncounter(BaseModel):
    encounter_id: str
    title: str


class CombatOptions(BaseModel):
    state: CombatStateView | None
    encounters: list[AvailableEncounter]


def public_combat_state(state: CombatState) -> CombatStateView:
    return CombatStateView(
        encounter_id=state.encounter_id,
        revision=state.revision,
        round_number=state.round_number,
        status=state.status,
        current_actor_id=state.current_actor_id,
        outcome_id=state.outcome_id,
        legal_actions=legal_actions(state, state.current_actor_id)
        if state.current_actor_id
        else (),
        combatants=tuple(
            CombatantView(
                actor_id=actor.actor_id,
                side=actor.side,
                health=actor.health,
                max_health=actor.max_health,
            )
            for actor in state.combatants
        ),
    )
