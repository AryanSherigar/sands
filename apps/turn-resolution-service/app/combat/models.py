"""Validated, immutable state and commands for a two-combatant encounter."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

Score = Annotated[int, Field(strict=True, ge=0, le=10000)]
Percent = Annotated[int, Field(strict=True, ge=0, le=100)]
Accumulator = Annotated[int, Field(strict=True, ge=0, le=99)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class Combatant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: Identifier
    side: Literal["player", "opponent"]
    max_health: Annotated[int, Field(strict=True, ge=1, le=10000)]
    health: Score
    attack: Score
    armor: Score
    speed: Score
    accuracy: Percent
    luck: Percent
    hit_accumulator: Accumulator = 0
    attack_tags: frozenset[str] = frozenset()
    required_attack_tag: Identifier | None = None

    @field_serializer("attack_tags")
    def serialize_attack_tags(self, tags: frozenset[str]) -> list[str]:
        return sorted(tags)

    @model_validator(mode="after")
    def validate_health(self) -> "Combatant":
        if self.health > self.max_health:
            raise ValueError("health exceeds maximum")
        return self


class CombatState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    encounter_id: Identifier
    rules_version: Literal[1] = 1
    revision: Annotated[int, Field(strict=True, ge=0)] = 0
    round_number: Annotated[int, Field(strict=True, ge=1)] = 1
    status: Literal["active", "player_defeated", "opponent_defeated"] = "active"
    combatants: tuple[Combatant, Combatant]
    turn_order: tuple[Identifier, Identifier]
    current_actor_id: Identifier | None
    outcome_id: Identifier | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "CombatState":
        if self.outcome_id is not None and self.status != "player_defeated":
            raise ValueError("only player defeat has a follow-up outcome")
        ids = {item.actor_id for item in self.combatants}
        sides = {item.side for item in self.combatants}
        if len(ids) != 2 or sides != {"player", "opponent"}:
            raise ValueError("combat needs two unique opposing actors")
        if len(set(self.turn_order)) != 2 or set(self.turn_order) != ids:
            raise ValueError("turn order must contain both actors")
        expected_order = tuple(
            item.actor_id
            for item in sorted(
                self.combatants, key=lambda item: (-item.speed, item.actor_id)
            )
        )
        if self.turn_order != expected_order:
            raise ValueError("turn order does not match initiative")
        if self.status == "active":
            if self.current_actor_id not in ids or any(
                item.health == 0 for item in self.combatants
            ):
                raise ValueError(
                    "active combat requires living actors and a current turn"
                )
        elif self.current_actor_id is not None:
            raise ValueError("ended combat cannot have a current turn")
        if self.status != "active":
            defeated = self.status.removesuffix("_defeated")
            if any(
                (item.health == 0) != (item.side == defeated)
                for item in self.combatants
            ):
                raise ValueError("combat outcome does not match health")
        return self


class CombatAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    client_action_id: UUID
    expected_revision: Annotated[int, Field(strict=True, ge=0)]
    actor_id: Identifier
    action_id: Literal["attack"]
    target_id: Identifier


class LegalAttack(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: Identifier
    action_id: Literal["attack"] = "attack"
    target_id: Identifier


class CombatEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: Identifier
    target_id: Identifier
    hit: bool
    immune: bool
    damage: Score
    target_health: Score


class CombatTransition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: CombatState
    event: CombatEvent
