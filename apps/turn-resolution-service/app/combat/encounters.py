"""Validate authored encounters and select only eligible authored outcomes."""

from typing import Annotated, Literal

from app.combat.models import Combatant, CombatState, Identifier
from app.combat.resolver import start_combat
from app.turn.expression_evaluator import evaluate
from app.turn.state_paths import set_field_value
from app.turn.steps.state_validator import validate_applied_change
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecoveryOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Identifier
    kind: Literal["recover"]
    health: Annotated[int, Field(strict=True, ge=1, le=10000)]
    location_id: Identifier | None = None
    condition: dict[str, object] | None = None


class EndingOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Identifier
    kind: Literal["end"]
    ending_id: Identifier
    condition: dict[str, object] | None = None


Outcome = Annotated[RecoveryOutcome | EndingOutcome, Field(discriminator="kind")]


class CombatEncounter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    encounter_id: Identifier
    title: Identifier = "Encounter"
    start_condition: dict[str, object]
    player: Combatant
    opponent: Combatant
    outcomes: tuple[Outcome, ...] = Field(min_length=1)
    fallback_outcome_id: Identifier

    @model_validator(mode="after")
    def validate_encounter(self) -> "CombatEncounter":
        ids = {outcome.id for outcome in self.outcomes}
        if len(ids) != len(self.outcomes) or self.fallback_outcome_id not in ids:
            raise ValueError("outcome IDs must be unique and include the fallback")
        if self.player.side != "player" or self.opponent.side != "opponent":
            raise ValueError("encounter needs a player and an opponent")
        if any(
            isinstance(outcome, RecoveryOutcome)
            and outcome.health > self.player.max_health
            for outcome in self.outcomes
        ):
            raise ValueError("recovery health exceeds player maximum")
        return self


def prepare_encounter(config: CombatEncounter, state: dict[str, object]) -> CombatState:
    """Start only when the authored condition and current health permit it."""
    if not evaluate(config.start_condition, state):
        raise ValueError("encounter is not available")
    player = state.get("player")
    health = player.get("health") if isinstance(player, dict) else None
    if type(health) is not int or not 0 < health <= config.player.max_health:
        raise ValueError("player health is invalid")
    combatant = Combatant.model_validate(
        {**config.player.model_dump(), "health": health}
    )
    return start_combat(config.encounter_id, combatant, config.opponent)


def choose_outcome(
    config: CombatEncounter, state: dict[str, object], suggested_id: str | None
) -> RecoveryOutcome | EndingOutcome:
    """Reject ineligible suggestions; use only an eligible authored fallback."""
    eligible = {
        outcome.id: outcome
        for outcome in config.outcomes
        if outcome.condition is None or evaluate(outcome.condition, state)
    }
    if suggested_id in eligible:
        return eligible[suggested_id]
    if config.fallback_outcome_id in eligible:
        return eligible[config.fallback_outcome_id]
    raise ValueError("no eligible fallback outcome")


def encounter_from_snapshot(
    snapshot: dict[str, object], encounter_id: str
) -> CombatEncounter:
    """Read exactly one encounter from the immutable server-side scenario snapshot."""
    config = snapshot.get("fantasy_combat")
    records = config.get("encounters") if isinstance(config, dict) else None
    if not isinstance(records, list):
        raise ValueError("combat is not configured")
    matches = [
        item
        for item in records
        if isinstance(item, dict) and item.get("encounter_id") == encounter_id
    ]
    if len(matches) != 1:
        raise ValueError("encounter is not configured uniquely")
    return CombatEncounter.model_validate(matches[0])


def with_player_health(
    state: dict[str, object], snapshot: dict[str, object], health: int
) -> dict[str, object]:
    """Validate trusted combat health against the authored schema and invariants."""
    schema = snapshot.get("state_schema")
    player = schema.get("player") if isinstance(schema, dict) else None
    fields = player.get("fields") if isinstance(player, dict) else None
    field = fields.get("health") if isinstance(fields, dict) else None
    if (
        not isinstance(field, dict)
        or field.get("type") != "number"
        or field.get("derived") is True
    ):
        raise ValueError("player health is not writable in the scenario schema")
    candidate = set_field_value(state, "player.health", health)
    validated = validate_applied_change("player.health", candidate, snapshot)
    if not validated.is_valid or validated.updated_state is None:
        raise ValueError("combat health violates scenario rules")
    previous = state.get("_last_changed_fields")
    changed = (
        {item for item in previous if isinstance(item, str)}
        if isinstance(previous, list)
        else set()
    )
    return {
        **validated.updated_state,
        "_last_changed_fields": sorted(changed | {"player.health"}),
    }
