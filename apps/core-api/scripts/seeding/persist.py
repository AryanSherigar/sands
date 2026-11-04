"""Writes a built scenario to the database (idempotent, replace-in-place).

Seed scripts use the ORM directly (see scripts/seed_stitch_scenarios.py); the
Router -> Service -> Repository layering applies to the request path, not here.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from app.db.models.end_condition import EndCondition
from app.db.models.entity import Entity
from app.db.models.fact import Fact
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.rule_invariant import RuleInvariant
from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_minigame import ScenarioMinigame
from app.db.models.scenario_rule_check import ScenarioRuleCheck
from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from app.services.scenario_edit_guard import ensure_not_publishing
from scripts.seeding.ids import ScenarioIds
from scripts.seeding.types import MapSeed, SeedableScenario
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# NOTE: Conditions are evaluated in created_at order, so each gets a distinct stamp.
CONDITION_STEP = timedelta(milliseconds=1)
CONDITION_EPOCH = datetime(2026, 10, 26, tzinfo=timezone.utc)
DRAFT_STATUS = "draft"
REQUEST_ONLY_FIELDS = {"expected_content_edited_at"}

CHILD_MODELS = (
    ScenarioCondition,
    EndCondition,
    RuleInvariant,
    ScenarioMinigame,
    ScenarioRuleCheck,
    ScenarioSheetRule,
    ScenarioMap,
    Entity,
)


async def clear_children(session: AsyncSession, scenario_id: uuid.UUID) -> None:
    """Facts, pins and connections go with their entities and map (ON DELETE CASCADE)."""
    for model in CHILD_MODELS:
        await session.execute(delete(model).where(model.scenario_id == scenario_id))


async def upsert_scenario(
    session: AsyncSession,
    built: SeedableScenario,
    creator_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Scenario:
    scenario = await session.get(Scenario, scenario_id)
    if scenario is None:
        scenario = Scenario(scenario_id=scenario_id, creator_id=creator_id)
        session.add(scenario)
    else:
        ensure_not_publishing(scenario)
    for column, value in built.scenario.items():
        setattr(scenario, column, value)
    scenario.status = DRAFT_STATUS
    await session.flush()
    return scenario


def add_entities(
    session: AsyncSession, built: SeedableScenario, ids: ScenarioIds
) -> None:
    for seed in built.entities:
        session.add(
            Entity(
                entity_id=ids.entity_id(seed.slug),
                scenario_id=ids.scenario_id,
                **seed.payload.model_dump(exclude=REQUEST_ONLY_FIELDS),
            )
        )


def add_facts(session: AsyncSession, built: SeedableScenario, ids: ScenarioIds) -> None:
    for index, fact in enumerate(built.facts):
        session.add(
            Fact(
                fact_id=ids.child_id("fact", index),
                scenario_id=ids.scenario_id,
                **fact.model_dump(exclude=REQUEST_ONLY_FIELDS),
            )
        )


def add_conditions(
    session: AsyncSession, built: SeedableScenario, ids: ScenarioIds
) -> None:
    for index, condition in enumerate(built.conditions):
        session.add(
            ScenarioCondition(
                condition_id=ids.child_id("condition", index),
                scenario_id=ids.scenario_id,
                label=condition.label,
                condition_expression=condition.condition_expression,
                narrator_instruction=condition.narrator_instruction,
                metadata_=condition.metadata,
                state_mutation=None,
                state_mutations=[
                    mutation.model_dump(mode="json")
                    for mutation in condition.state_mutations
                ],
                is_one_shot=condition.is_one_shot,
                sensory_cue=condition.sensory_cue,
                cut_ambient=condition.cut_ambient,
                silence_duration_ms=condition.silence_duration_ms,
                created_at=CONDITION_EPOCH + index * CONDITION_STEP,
            )
        )


def add_endings_and_invariants(
    session: AsyncSession, built: SeedableScenario, ids: ScenarioIds
) -> None:
    for index, ending in enumerate(built.end_conditions):
        session.add(
            EndCondition(
                end_condition_id=ids.child_id("ending", index),
                scenario_id=ids.scenario_id,
                **ending.model_dump(),
            )
        )
    for index, invariant in enumerate(built.invariants):
        session.add(
            RuleInvariant(
                invariant_id=ids.child_id("invariant", index),
                scenario_id=ids.scenario_id,
                **invariant.model_dump(),
            )
        )


def add_minigames(
    session: AsyncSession, built: SeedableScenario, ids: ScenarioIds
) -> None:
    for index, minigame in enumerate(built.minigames):
        session.add(
            ScenarioMinigame(
                minigame_id=ids.child_id("minigame", index),
                scenario_id=ids.scenario_id,
                **minigame.model_dump(mode="json"),
            )
        )


def add_tool_rows(
    session: AsyncSession, built: SeedableScenario, ids: ScenarioIds
) -> None:
    for index, check in enumerate(built.rule_checks):
        session.add(
            ScenarioRuleCheck(
                check_id=ids.child_id("check", index),
                scenario_id=ids.scenario_id,
                **check.model_dump(),
            )
        )
    for rule in built.sheet_rules:
        session.add(
            ScenarioSheetRule(
                rule_id=ids.child_id("sheet-rule", rule.key),
                scenario_id=ids.scenario_id,
                **rule.model_dump(),
            )
        )


async def add_map(session: AsyncSession, map_seed: MapSeed, ids: ScenarioIds) -> None:
    map_id = ids.child_id("map", map_seed.name)
    session.add(
        ScenarioMap(
            map_id=map_id,
            scenario_id=ids.scenario_id,
            name=map_seed.name,
            image_url=map_seed.image_url,
            display_order=map_seed.display_order,
        )
    )
    await session.flush()
    for pin in map_seed.pins:
        session.add(
            MapPin(
                pin_id=ids.child_id("pin", pin.slug),
                map_id=map_id,
                scenario_id=ids.scenario_id,
                entity_id=ids.entity_id(pin.slug),
                x=pin.x,
                y=pin.y,
                is_start_location=pin.slug == map_seed.start_slug,
            )
        )
    for first, second in map_seed.connections:
        low, high = sorted((ids.entity_id(first), ids.entity_id(second)))
        session.add(
            MapConnection(
                connection_id=ids.child_id("connection", f"{first}:{second}"),
                scenario_id=ids.scenario_id,
                entity_id_a=low,
                entity_id_b=high,
            )
        )


async def persist(
    session: AsyncSession,
    built: SeedableScenario,
    creator_id: uuid.UUID,
    ids: ScenarioIds,
    maps: Sequence[MapSeed],
) -> None:
    await upsert_scenario(session, built, creator_id, ids.scenario_id)
    await clear_children(session, ids.scenario_id)
    add_entities(session, built, ids)
    await session.flush()
    add_facts(session, built, ids)
    add_conditions(session, built, ids)
    add_endings_and_invariants(session, built, ids)
    add_minigames(session, built, ids)
    add_tool_rows(session, built, ids)
    for map_seed in maps:
        await add_map(session, map_seed, ids)
    await session.flush()
