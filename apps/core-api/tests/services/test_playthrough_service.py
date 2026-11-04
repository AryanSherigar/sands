"""Unit/integration tests for PlaythroughService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.entity import Entity
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.participant import Participant
from app.db.models.scenario import Scenario
from app.db.models.share import PlaythroughShare
from app.exceptions.playthrough_exceptions import (
    InvalidSetupValuesError,
    ScenarioNotPublishedError,
)
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.models.playthrough import PlaythroughCreate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.invariant_repo import InvariantRepo
from app.repositories.map_repo import MapRepo
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.share_repo import ShareRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.services import default_music
from app.services.playthrough_service import (
    FALLBACK_PLAYER_NAME,
    NEWBIE_PLAYER_ENTITY_KEY,
    PlaythroughService,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_service(db_session: AsyncSession) -> PlaythroughService:
    return PlaythroughService(
        playthrough_repo=PlaythroughRepo(db_session),
        participant_repo=ParticipantRepo(db_session),
        scenario_repo=ScenarioRepo(db_session),
        share_repo=ShareRepo(db_session),
        turn_log_repo=TurnLogRepo(db_session),
        entity_repo=EntityRepo(db_session),
        fact_repo=FactRepo(db_session),
        condition_repo=ConditionRepo(db_session),
        invariant_repo=InvariantRepo(db_session),
        end_condition_repo=EndConditionRepo(db_session),
        map_repo=MapRepo(db_session),
        minigame_repo=MinigameRepo(db_session),
        scenario_music_repo=ScenarioMusicRepo(db_session),
        memory_outbox_repo=MemoryOutboxRepo(db_session),
        user_repo=UserRepo(db_session),
    )


async def _get_register_row(
    db_session: AsyncSession, playthrough_id: uuid.UUID
) -> MemoryOutbox:
    rows = (
        (
            await db_session.execute(
                select(MemoryOutbox).where(
                    MemoryOutbox.playthrough_id == playthrough_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    return rows[0]


async def _make_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev User"
    )


async def _make_scenario(
    db_session: AsyncSession,
    creator_id: uuid.UUID,
    status: str = "published",
    setup_schema: list[object] | None = None,
    player_count_support: str = "solo",
    narration_font: str | None = None,
    action_chips: list[str] | None = None,
) -> Scenario:
    scenario = Scenario(
        creator_id=creator_id,
        title="Dragon's Lair",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support=player_count_support,
        status=status,
        setup_schema=setup_schema or [],
        narrator_persona="A grim narrator.",
        world_data={"lore": "A cave full of gold."},
        narration_font=narration_font,
        action_chips=action_chips or [],
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.mark.asyncio
async def test_create_playthrough_happy_path(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert result.scenario_version == scenario.current_version
    pinned = (
        await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    ).scenario_snapshot
    assert pinned["narrator_persona"] == "A grim narrator."
    assert "narrator_persona" not in result.scenario_snapshot
    assert result.scenario_snapshot["world_data"] == {"lore": "A cave full of gold."}
    assert result.scenario_snapshot["mode"] == "newbie"
    assert pinned["entities"] == []
    assert pinned["mood_tags"] == []
    assert pinned["opening_scene"] is None
    assert "facts" not in pinned
    assert "scenario_conditions" not in pinned
    assert "rule_invariants" not in pinned
    assert result.state["setup"] == {}
    assert result.status == "active"

    participant_repo = ParticipantRepo(db_session)
    participant = await participant_repo.get_by_playthrough_and_user(
        result.playthrough_id, user.user_id
    )
    assert participant is not None
    assert participant.role == "owner"
    assert participant.turn_order_position == 1


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_narration_font(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session, user.user_id, narration_font="special-elite"
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert result.scenario_snapshot["narration_font"] == "special-elite"


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_action_chips(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        action_chips=["I explore the ancient ruins.", "I draw my sword."],
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert result.scenario_snapshot["action_chips"] == [
        "I explore the ancient ruins.",
        "I draw my sword.",
    ]


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_empty_action_chips_by_default(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert result.scenario_snapshot["action_chips"] == []


@pytest.mark.asyncio
async def test_create_playthrough_scenario_not_published(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id, status="draft")

    with pytest.raises(ScenarioNotPublishedError):
        await service.create_playthrough(
            user_id=user.user_id,
            data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
        )


@pytest.mark.asyncio
async def test_create_playthrough_scenario_not_found(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)

    with pytest.raises(ScenarioNotFoundError):
        await service.create_playthrough(
            user_id=user.user_id,
            data=PlaythroughCreate(scenario_id=uuid.uuid4(), setup_values={}),
        )


@pytest.mark.asyncio
async def test_create_playthrough_missing_required_setup_field(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        setup_schema=[
            {"field_key": "character_class", "type": "text", "required": True}
        ],
    )

    with pytest.raises(InvalidSetupValuesError):
        await service.create_playthrough(
            user_id=user.user_id,
            data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
        )


@pytest.mark.asyncio
async def test_create_playthrough_invalid_select_value(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        setup_schema=[
            {
                "field_key": "difficulty",
                "type": "select",
                "required": True,
                "options": ["easy", "hard"],
            }
        ],
    )

    with pytest.raises(InvalidSetupValuesError):
        await service.create_playthrough(
            user_id=user.user_id,
            data=PlaythroughCreate(
                scenario_id=scenario.scenario_id,
                setup_values={"difficulty": "impossible"},
            ),
        )


@pytest.mark.asyncio
async def test_create_multiple_concurrent_playthroughs(db_session: AsyncSession):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    first = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    second = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert first.playthrough_id != second.playthrough_id


@pytest.mark.asyncio
async def test_create_playthrough_multiplayer_scenario_solo_start(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session, user.user_id, player_count_support="multiplayer"
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    participants = await ParticipantRepo(db_session).list_by_playthrough(
        result.playthrough_id
    )
    assert len(participants) == 1
    assert participants[0].role == "owner"


@pytest.mark.asyncio
async def test_create_playthrough_with_multi_select_and_object_options(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        setup_schema=[
            {
                "key": "role",
                "type": "single_select",
                "required": True,
                "options": [{"value": "mage", "label": "Mage"}],
            },
            {
                "key": "skills",
                "type": "multi_select",
                "required": True,
                "options": [
                    {"value": "fireball", "label": "Fireball"},
                    {"value": "teleport", "label": "Teleport"},
                ],
            },
        ],
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(
            scenario_id=scenario.scenario_id,
            setup_values={"role": "mage", "skills": ["fireball", "teleport"]},
        ),
    )

    assert result.state["setup"]["role"] == "mage"
    assert result.state["setup"]["skills"] == ["fireball", "teleport"]


@pytest.mark.asyncio
async def test_create_playthrough_master_mode_snapshot_includes_entities_and_rules(
    db_session: AsyncSession,
):
    """A master-mode scenario's entities, non-hidden facts, active
    conditions, and rule invariants are pinned into scenario_snapshot at
    playthrough creation (master-mode-turn-pipeline.spec.md) — TRS never
    reads Scenario or its sub-resource tables directly during a turn."""
    from app.models.condition import ConditionCreate
    from app.models.end_condition import EndConditionCreate
    from app.models.entity import EntityCreate
    from app.models.fact import FactCreate
    from app.models.invariant import InvariantCreate
    from app.models.minigame import DodgeConfig, MinigameCreate
    from app.services.condition_service import ConditionService
    from app.services.end_condition_service import EndConditionService
    from app.services.entity_service import EntityService
    from app.services.fact_service import FactService
    from app.services.invariant_service import InvariantService
    from app.services.minigame_service import MinigameService

    user = await _make_user(db_session)
    scenario = Scenario(
        creator_id=user.user_id,
        title="The Hollow Cairn",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        narrator_persona="Dry humor.",
        state_schema={
            "player": {"type": "object", "fields": {"health": {"type": "number"}}}
        },
    )
    db_session.add(scenario)
    await db_session.flush()

    entity_service = EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    )
    warden = await entity_service.create_entity(
        scenario.scenario_id,
        user.user_id,
        EntityCreate(
            entity_type="character",
            canonical_name="The Warden",
            aliases=["the guardian"],
            description="A tireless sentinel bound to the cairn.",
        ),
    )
    relic = await entity_service.create_entity(
        scenario.scenario_id,
        user.user_id,
        EntityCreate(
            entity_type="item",
            canonical_name="the Ashen Crown",
            description="A relic said to bind the cairn's warden.",
        ),
    )
    fact_service = FactService(
        FactRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )
    await fact_service.create_fact(
        scenario.scenario_id,
        user.user_id,
        FactCreate(
            subject_entity_id=warden.entity_id,
            predicate="guards",
            object_entity_id=relic.entity_id,
        ),
    )
    # Hidden facts are secrets, not codex entries -- must never reach the
    # snapshot the play screen renders from.
    await fact_service.create_fact(
        scenario.scenario_id,
        user.user_id,
        FactCreate(
            subject_entity_id=warden.entity_id,
            predicate="fears",
            object_literal="sunlight",
            hidden=True,
        ),
    )
    condition_service = ConditionService(
        ConditionRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )
    await condition_service.create_condition(
        scenario.scenario_id,
        user.user_id,
        ConditionCreate(label="Warden Is Wary", narrator_instruction="Watchful."),
    )
    invariant_service = InvariantService(
        InvariantRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )
    await invariant_service.create_invariant(
        scenario.scenario_id,
        user.user_id,
        InvariantCreate(
            label="Health floor",
            invariant_expression={"field": "player.health", "op": ">=", "value": 0},
            applies_to="global",
            narrator_text="Health cannot fall below zero.",
        ),
    )

    end_condition_service = EndConditionService(
        EndConditionRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )
    # Created out of priority order: the snapshot must reflect priority
    # ascending, not creation order (master-mode-end-conditions.spec.md).
    await end_condition_service.create_end_condition(
        scenario.scenario_id,
        user.user_id,
        EndConditionCreate(
            outcome_tag="lose",
            outcome_title="Consumed",
            outcome_text="The cairn does not release what it takes.",
            priority=5,
        ),
    )
    await end_condition_service.create_end_condition(
        scenario.scenario_id,
        user.user_id,
        EndConditionCreate(
            outcome_tag="win",
            outcome_title="The Ashen Ending",
            outcome_text="The Warden kneels.",
            priority=1,
        ),
    )
    await end_condition_service.create_end_condition(
        scenario.scenario_id,
        user.user_id,
        EndConditionCreate(
            outcome_tag="win",
            outcome_title="The Vigil's Ending",
            outcome_text="You relieve it.",
            is_secret=True,
            priority=3,
        ),
    )

    minigame_service = MinigameService(
        MinigameRepo(db_session),
        EntityRepo(db_session),
        ScenarioRepo(db_session),
    )
    # Created out of priority order: the snapshot must reflect priority
    # ascending, not creation order (master-mode-minigames.spec.md).
    await minigame_service.create_minigame(
        scenario.scenario_id,
        user.user_id,
        MinigameCreate(
            label="Warden's Onslaught",
            minigame_type="dodge",
            outcome_mode="binary",
            win_mutation={"path": "player.health", "op": "set", "value": 100},
            lose_mutation={"path": "player.health", "op": "decrement", "value": 15},
            dodge_config=DodgeConfig(difficulty=3),
            priority=2,
        ),
    )
    await minigame_service.create_minigame(
        scenario.scenario_id,
        user.user_id,
        MinigameCreate(
            label="Rune Trial",
            minigame_type="dodge",
            outcome_mode="binary",
            win_mutation={"path": "player.health", "op": "set", "value": 100},
            lose_mutation={"path": "player.health", "op": "decrement", "value": 5},
            dodge_config=DodgeConfig(difficulty=1),
            priority=0,
        ),
    )

    service = await _make_service(db_session)
    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    snapshot = (
        await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    ).scenario_snapshot
    assert snapshot["mode"] == "master"
    assert len(snapshot["entities"]) == 2
    assert snapshot["entities"][0]["entity_id"] == str(warden.entity_id)
    assert snapshot["entities"][0]["entity_type"] == "character"
    assert snapshot["entities"][0]["aliases"] == ["the guardian"]
    assert snapshot["entities"][0]["description"] == (
        "A tireless sentinel bound to the cairn."
    )
    assert len(snapshot["facts"]) == 1
    assert snapshot["facts"][0]["text"] == "The Warden guards the Ashen Crown."
    assert len(snapshot["scenario_conditions"]) == 1
    assert snapshot["scenario_conditions"][0]["label"] == "Warden Is Wary"
    assert len(snapshot["rule_invariants"]) == 1
    assert snapshot["rule_invariants"][0]["narrator_text"] == (
        "Health cannot fall below zero."
    )
    assert [ec["outcome_title"] for ec in snapshot["end_conditions"]] == [
        "The Ashen Ending",
        "The Vigil's Ending",
        "Consumed",
    ]
    assert all(uuid.UUID(ec["end_condition_id"]) for ec in snapshot["end_conditions"])
    assert len({ec["end_condition_id"] for ec in snapshot["end_conditions"]}) == 3
    assert [m["label"] for m in snapshot["scenario_minigames"]] == [
        "Rune Trial",
        "Warden's Onslaught",
    ]


@pytest.mark.asyncio
async def test_load_map_data_groups_pins_by_map_without_n_plus_1(
    db_session: AsyncSession,
) -> None:
    """Regression test for MED-03: pins from multiple maps must be correctly
    attributed to their own map_id via a single batch query, not a per-map
    loop."""
    from app.db.models.entity import Entity
    from app.db.models.map_pin import MapPin
    from app.db.models.scenario_map import ScenarioMap

    user = await _make_user(db_session)
    scenario = Scenario(
        creator_id=user.user_id,
        title="Twin Halls",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        narrator_persona="Terse.",
        state_schema={},
    )
    db_session.add(scenario)
    await db_session.flush()

    map_one = ScenarioMap(scenario_id=scenario.scenario_id, name="East Wing")
    map_two = ScenarioMap(scenario_id=scenario.scenario_id, name="West Wing")
    db_session.add_all([map_one, map_two])
    await db_session.flush()

    entrance = Entity(
        scenario_id=scenario.scenario_id,
        entity_type="location",
        canonical_name="Entrance",
    )
    vault = Entity(
        scenario_id=scenario.scenario_id, entity_type="location", canonical_name="Vault"
    )
    db_session.add_all([entrance, vault])
    await db_session.flush()

    pin_one = MapPin(
        map_id=map_one.map_id,
        scenario_id=scenario.scenario_id,
        entity_id=entrance.entity_id,
        x=1.0,
        y=1.0,
        is_start_location=True,
    )
    pin_two = MapPin(
        map_id=map_two.map_id,
        scenario_id=scenario.scenario_id,
        entity_id=vault.entity_id,
        x=2.0,
        y=2.0,
    )
    db_session.add_all([pin_one, pin_two])
    await db_session.flush()

    service = await _make_service(db_session)

    async def _fail_if_called(*args: object, **kwargs: object) -> list[object]:
        raise AssertionError("list_pins_by_map must not be called (N+1 regression)")

    service.map_repo.list_pins_by_map = _fail_if_called

    map_data = await service._load_map_data(scenario.scenario_id)

    pins_by_map = {p["map_id"]: p for p in map_data.pins}
    assert pins_by_map[str(map_one.map_id)]["entity_id"] == str(entrance.entity_id)
    assert pins_by_map[str(map_two.map_id)]["entity_id"] == str(vault.entity_id)
    assert map_data.start_entity_id == str(entrance.entity_id)


@pytest.mark.asyncio
async def test_participant_unique_user_constraint_enforced(
    db_session: AsyncSession,
) -> None:
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)
    playthrough_resp = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    duplicate_participant = Participant(
        playthrough_id=playthrough_resp.playthrough_id,
        user_id=user.user_id,
        role="joined",
        turn_order_position=2,
    )
    participant_repo = ParticipantRepo(db_session)
    with pytest.raises(IntegrityError):
        await participant_repo.create(duplicate_participant)


@pytest.mark.asyncio
async def test_participant_unique_turn_order_constraint_enforced(
    db_session: AsyncSession,
) -> None:
    service = await _make_service(db_session)
    user1 = await _make_user(db_session)
    user2 = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user1.user_id)
    playthrough_resp = await service.create_playthrough(
        user_id=user1.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    duplicate_position_participant = Participant(
        playthrough_id=playthrough_resp.playthrough_id,
        user_id=user2.user_id,
        role="joined",
        turn_order_position=1,
    )
    participant_repo = ParticipantRepo(db_session)
    with pytest.raises(IntegrityError):
        await participant_repo.create(duplicate_position_participant)


@pytest.mark.asyncio
async def test_join_playthrough_idempotent_for_same_user(
    db_session: AsyncSession,
) -> None:
    service = await _make_service(db_session)
    owner = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session, owner.user_id, player_count_support="both"
    )
    playthrough_resp = await service.create_playthrough(
        user_id=owner.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    share = PlaythroughShare(
        playthrough_id=playthrough_resp.playthrough_id,
        share_token="join-token-123",
        mode="join",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(share)
    await db_session.flush()

    joiner = await _make_user(db_session)
    first_join = await service.join_playthrough("join-token-123", joiner.user_id)
    second_join = await service.join_playthrough("join-token-123", joiner.user_id)

    assert first_join.participant_id == second_join.participant_id
    assert len(first_join.participants) == 2
    assert len(second_join.participants) == 2


@pytest.mark.asyncio
async def test_join_playthrough_sequential_turn_order_positions(
    db_session: AsyncSession,
) -> None:
    service = await _make_service(db_session)
    owner = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session, owner.user_id, player_count_support="both"
    )
    playthrough_resp = await service.create_playthrough(
        user_id=owner.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    share = PlaythroughShare(
        playthrough_id=playthrough_resp.playthrough_id,
        share_token="multi-join-token",
        mode="join",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(share)
    await db_session.flush()

    user2 = await _make_user(db_session)
    user3 = await _make_user(db_session)

    await service.join_playthrough("multi-join-token", user2.user_id)
    resp3 = await service.join_playthrough("multi-join-token", user3.user_id)

    positions = {p.user_id: p.turn_order_position for p in resp3.participants}
    assert positions[owner.user_id] == 1
    assert positions[user2.user_id] == 2
    assert positions[user3.user_id] == 3


async def _make_master_scenario_with_player(
    db_session: AsyncSession, user_id: uuid.UUID
) -> tuple[Scenario, uuid.UUID]:
    scenario = Scenario(
        creator_id=user_id,
        title="Epic Quest",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        setup_schema=[
            {"key": "character_name", "label": "Hero Name", "is_character_name": True},
            {"key": "class", "label": "Class", "predicate": "has_class"},
        ],
    )
    db_session.add(scenario)
    await db_session.flush()
    player = await EntityRepo(db_session).create(
        Entity(
            scenario_id=scenario.scenario_id,
            entity_type="character",
            canonical_name="Default Hero",
            aliases=["The Chosen"],
            is_player=True,
        )
    )
    return scenario, player.entity_id


@pytest.mark.asyncio
async def test_create_playthrough_player_setup_fact_attachment(
    db_session: AsyncSession,
) -> None:
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario, player_entity_id = await _make_master_scenario_with_player(
        db_session, user.user_id
    )
    res = await service.create_playthrough(
        user.user_id,
        PlaythroughCreate(
            scenario_id=scenario.scenario_id,
            setup_values={"character_name": "Valerius", "class": "Paladin"},
        ),
    )
    ent = res.scenario_snapshot["entities"][0]
    assert ent["canonical_name"] == "Valerius"
    assert "Default Hero" in ent["aliases"]
    assert res.state["setup"]["character_name"] == "Valerius"
    row = await _get_register_row(db_session, res.playthrough_id)
    payload = row.payload
    assert payload["player_entity"]["canonical_name"] == "Valerius"
    assert payload["player_entity"]["authored_entity_id"] == str(player_entity_id)
    assert payload["player_entity"]["entity_type"] == "character"
    assert "Default Hero" in payload["player_entity"]["aliases"]
    assert payload["setup_facts"][0]["predicate"] == "has_class"
    assert payload["setup_facts"][0]["object_literal"] == "Paladin"
    assert payload["setup_facts"][0]["subject_entity_id"] == str(player_entity_id)


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_music_tracks_newbie_mode(
    db_session: AsyncSession,
):
    """Newbie-mode scenarios never write scenario_music rows -- every mood
    must still resolve to a real, playable built-in default track."""
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    music_tracks = result.scenario_snapshot["music_tracks"]
    assert set(music_tracks) == {
        "peaceful",
        "mystery",
        "tension",
        "combat",
        "melancholy",
        "triumph",
    }
    for mood, track_url in music_tracks.items():
        assert track_url == default_music.default_track_url(mood)


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_music_tracks_master_mode_untouched(
    db_session: AsyncSession,
):
    """An untouched mood slot in a master-mode scenario resolves to the same
    built-in default as a newbie-mode scenario."""
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = Scenario(
        creator_id=user.user_id,
        title="The Hollow Cairn",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        narrator_persona="Dry humor.",
    )
    db_session.add(scenario)
    await db_session.flush()

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    music_tracks = result.scenario_snapshot["music_tracks"]
    for mood, track_url in music_tracks.items():
        assert track_url == default_music.default_track_url(mood)


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_explicit_default_selection(
    db_session: AsyncSession,
):
    """A persisted source='default' row resolves the same as an untouched
    slot -- proves 'explicitly chose default' and 'never touched' no longer
    collapse into different behavior."""
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)
    await ScenarioMusicRepo(db_session).upsert(
        scenario_id=scenario.scenario_id,
        mood="peaceful",
        source="default",
        track_url=None,
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    music_tracks = result.scenario_snapshot["music_tracks"]
    assert music_tracks["peaceful"] == default_music.default_track_url("peaceful")


@pytest.mark.asyncio
async def test_create_playthrough_snapshots_custom_uploaded_music_track(
    db_session: AsyncSession,
):
    """A creator-uploaded track's URL passes through the snapshot verbatim,
    not the built-in default."""
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)
    custom_url = "https://storage.googleapis.com/test-bucket/scenario-music/custom.mp3"
    await ScenarioMusicRepo(db_session).upsert(
        scenario_id=scenario.scenario_id,
        mood="combat",
        source="upload",
        track_url=custom_url,
        duration_seconds=45.0,
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    music_tracks = result.scenario_snapshot["music_tracks"]
    assert music_tracks["combat"] == custom_url


@pytest.mark.asyncio
async def test_create_playthrough_queues_register_row_for_newbie_scenario(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    row = await _get_register_row(db_session, result.playthrough_id)
    assert row.item_kind == "register_playthrough"
    assert row.sequence == 0
    assert row.turn_id is None
    assert row.delivered_at is None
    assert row.attempt_count == 0
    assert row.payload == {
        "scenario_id": str(scenario.scenario_id),
        "publish_revision": 0,
        "player_entity": {
            "authored_entity_id": str(
                uuid.uuid5(result.playthrough_id, NEWBIE_PLAYER_ENTITY_KEY)
            ),
            "canonical_name": "Dev User",
            "aliases": [],
            "entity_type": "character",
        },
        "setup_facts": [],
        "participants": [
            {
                "participant_id": str(result.participant_id),
                "display_name": "Dev User",
            }
        ],
        "tracked_fields": [],
    }


@pytest.mark.asyncio
async def test_newbie_player_entity_uses_the_chosen_character_name(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        setup_schema=[
            {
                "key": "character_name",
                "label": "Name",
                "type": "text",
                "required": False,
            }
        ],
    )

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(
            scenario_id=scenario.scenario_id,
            setup_values={"character_name": "Ilsa Marrow"},
        ),
    )

    player = (await _get_register_row(db_session, result.playthrough_id)).payload[
        "player_entity"
    ]
    assert player["canonical_name"] == "Ilsa Marrow"
    assert player["aliases"] == ["Dev User"]
    assert player["entity_type"] == "character"


@pytest.mark.asyncio
async def test_newbie_player_entity_falls_back_when_there_is_no_name(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    user.display_name = "  "
    await db_session.flush()
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    player = (await _get_register_row(db_session, result.playthrough_id)).payload[
        "player_entity"
    ]
    assert player["canonical_name"] == FALLBACK_PLAYER_NAME
    assert player["aliases"] == []


@pytest.mark.asyncio
async def test_newbie_player_entity_id_is_stable_per_playthrough(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    first = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    second = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    ids = {
        (await _get_register_row(db_session, r.playthrough_id)).payload[
            "player_entity"
        ]["authored_entity_id"]
        for r in (first, second)
    }
    assert len(ids) == 2


@pytest.mark.asyncio
async def test_create_playthrough_pins_publish_revision_on_playthrough_and_row(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)
    scenario.publish_revision = 3
    await db_session.flush()

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    playthrough = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    row = await _get_register_row(db_session, result.playthrough_id)
    assert playthrough.memory_publish_revision == 3
    assert row.payload["publish_revision"] == 3


@pytest.mark.asyncio
async def test_create_playthrough_master_without_player_entity_has_null_player(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = Scenario(
        creator_id=user.user_id,
        title="No Hero",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
    )
    db_session.add(scenario)
    await db_session.flush()

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    row = await _get_register_row(db_session, result.playthrough_id)
    assert row.payload["player_entity"] is None
    assert row.payload["setup_facts"] == []


@pytest.mark.asyncio
async def test_register_row_lists_master_tracked_fields_from_state_schema(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = Scenario(
        creator_id=user.user_id,
        title="Tracked",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        state_schema={
            "player": {"type": "object", "fields": {"health": {"type": "number"}}},
            "alarm_level": {"type": "number"},
        },
    )
    db_session.add(scenario)
    await db_session.flush()

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    row = await _get_register_row(db_session, result.playthrough_id)
    assert row.payload["tracked_fields"] == ["alarm_level", "health", "player"]


@pytest.mark.asyncio
async def test_register_row_has_no_tracked_fields_for_newbie_scenario(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    row = await _get_register_row(db_session, result.playthrough_id)
    assert row.payload["tracked_fields"] == []


@pytest.mark.asyncio
async def test_create_playtest_of_draft_scenario_also_queues_register_row(
    db_session: AsyncSession,
):
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id, status="draft")

    result = await service.create_playtest(
        scenario_id=scenario.scenario_id, user_id=user.user_id, setup_values={}
    )

    playthrough = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    row = await _get_register_row(db_session, result.playthrough_id)
    assert playthrough.memory_publish_revision == 0
    assert row.payload["publish_revision"] == 0


@pytest.mark.asyncio
async def test_create_playthrough_makes_no_memory_service_call(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("playthrough creation must not call the memory service")

    monkeypatch.setattr("app.integrations.memory_client._get_client", _fail)
    service = await _make_service(db_session)
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert result.status == "active"


def test_snapshot_fact_pins_when_active_only_for_conditional_facts():
    from types import SimpleNamespace

    from app.services.playthrough_service import _snapshot_fact

    subject_id = uuid.uuid4()
    names = {str(subject_id): "The Warden"}
    expression = {"field": "flags.alarm", "op": "==", "value": True}

    def _fact(when_active):
        return SimpleNamespace(
            fact_id=uuid.uuid4(),
            subject_entity_id=subject_id,
            object_entity_id=None,
            object_literal="vigilant",
            predicate="is",
            when_active=when_active,
        )

    conditional = _snapshot_fact(_fact(expression), names)
    unconditional = _snapshot_fact(_fact(None), names)

    assert conditional["when_active"] == expression
    assert conditional["text"] == "The Warden is vigilant."
    assert "when_active" not in unconditional


@pytest.mark.asyncio
async def test_newbie_snapshot_carries_cards_opening_and_mood(
    db_session: AsyncSession,
):
    user = await _make_user(db_session)
    scenario = await _make_scenario(
        db_session,
        user.user_id,
        setup_schema=[{"key": "name", "label": "Name", "type": "text"}],
    )
    scenario.opening_scene = "Welcome to the lighthouse, {player_name}."
    scenario.mood_tags = ["eerie", "tense"]
    scenario.guide_seen_features = ["triggers"]
    mara = await EntityRepo(db_session).create(
        Entity(
            scenario_id=scenario.scenario_id,
            entity_type="character",
            canonical_name="Mara",
            aliases=["Mara", "the keeper"],
            description="The keeper.",
            is_player=False,
        )
    )
    service = await _make_service(db_session)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(
            scenario_id=scenario.scenario_id, setup_values={"name": "Ik"}
        ),
    )

    pinned = (
        await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    ).scenario_snapshot
    assert pinned["mode"] == "newbie"
    assert pinned["entities"] == [
        {
            "entity_id": str(mara.entity_id),
            "entity_type": "character",
            "canonical_name": "Mara",
            "aliases": ["Mara", "the keeper"],
            "description": "The keeper.",
            "attributes_schema": {},
            "obtainable": None,
            "narrator_instruction": None,
            "is_player": False,
        }
    ]
    assert pinned["opening_scene"] == "Welcome to the lighthouse, Ik."
    assert pinned["mood_tags"] == ["eerie", "tense"]
    assert "facts" not in pinned
    assert "guide_seen_features" not in pinned
    assert "guide_seen_features" not in result.scenario_snapshot
    assert result.state["narrative"]["opening_prompt"] == pinned["opening_scene"]


@pytest.mark.asyncio
async def test_master_snapshot_also_carries_opening_and_mood(
    db_session: AsyncSession,
):
    user = await _make_user(db_session)
    scenario = await _make_scenario(db_session, user.user_id)
    scenario.mode = "master"
    scenario.complexity_tier = "master"
    scenario.opening_scene = "You wake, {player_name}."
    scenario.mood_tags = ["epic"]
    service = await _make_service(db_session)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    pinned = (
        await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    ).scenario_snapshot
    assert pinned["opening_scene"] == "You wake, Adventurer."
    assert pinned["mood_tags"] == ["epic"]
    assert "facts" in pinned


MODE_SWITCH_STATE_SCHEMA = {
    "health": {
        "type": "number",
        "initial": 7,
        "min": 0,
        "max": 10,
        "display": {"kind": "meter"},
    }
}
MODE_SWITCH_ATTRIBUTES = {"stamina": {"type": "number", "initial": 3}}
MODE_SWITCH_EXPRESSION = {"field": "health", "op": "<=", "value": 0}


async def _make_master_scenario_with_rows(
    db_session: AsyncSession, creator_id: uuid.UUID
) -> Scenario:
    from app.db.models.end_condition import EndCondition
    from app.db.models.rule_invariant import RuleInvariant
    from app.db.models.scenario_condition import ScenarioCondition
    from app.db.models.scenario_sheet_rule import ScenarioSheetRule
    from app.tools import rule_sheet as rule_sheet_tool  # noqa: F401

    scenario = Scenario(
        creator_id=creator_id,
        title="Switch Test",
        mode="master",
        complexity_tier="intermediate",
        player_count_support="solo",
        status="published",
        state_schema=MODE_SWITCH_STATE_SCHEMA,
        enabled_tools=["status_hud", "rule_sheet"],
    )
    db_session.add(scenario)
    await db_session.flush()
    db_session.add_all(
        [
            Entity(
                scenario_id=scenario.scenario_id,
                entity_type="character",
                canonical_name="Mara",
                attributes_schema=MODE_SWITCH_ATTRIBUTES,
            ),
            ScenarioCondition(
                scenario_id=scenario.scenario_id,
                label="Low health",
                condition_expression=MODE_SWITCH_EXPRESSION,
                narrator_instruction="Mara winces.",
            ),
            EndCondition(
                scenario_id=scenario.scenario_id,
                condition_expression=MODE_SWITCH_EXPRESSION,
                outcome_tag="lose",
                outcome_title="Gone",
                outcome_text="The light fades.",
            ),
            RuleInvariant(
                scenario_id=scenario.scenario_id,
                label="Floor",
                invariant_expression={"field": "health", "op": ">=", "value": 0},
                applies_to="global",
                narrator_text="Never below zero.",
            ),
            ScenarioSheetRule(
                scenario_id=scenario.scenario_id,
                key="r1",
                number=1,
                text="Do not whistle.",
            ),
        ]
    )
    await db_session.flush()
    return scenario


async def _start_and_pin(
    db_session: AsyncSession, scenario: Scenario
) -> dict[str, object]:
    service = await _make_service(db_session)
    result = await service.create_playthrough(
        user_id=scenario.creator_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    pinned = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    return pinned.scenario_snapshot


MASTER_ONLY_SNAPSHOT_KEYS = (
    "scenario_conditions",
    "rule_invariants",
    "end_conditions",
    "facts",
    "scenario_minigames",
    "sheet_rules",
)


@pytest.mark.asyncio
async def test_newbie_snapshot_omits_state_schema_attributes_schema_and_tools(
    db_session: AsyncSession,
):
    user = await _make_user(db_session)
    scenario = await _make_master_scenario_with_rows(db_session, user.user_id)
    scenario.mode = "newbie"
    await db_session.flush()

    snapshot = await _start_and_pin(db_session, scenario)

    assert snapshot["mode"] == "newbie"
    assert snapshot["state_schema"] == {}
    assert snapshot["enabled_tools"] == []
    assert [e["attributes_schema"] for e in snapshot["entities"]] == [{}]
    assert [e["canonical_name"] for e in snapshot["entities"]] == ["Mara"]
    for key in MASTER_ONLY_SNAPSHOT_KEYS:
        assert key not in snapshot


@pytest.mark.asyncio
async def test_newbie_playthrough_state_has_no_master_initials(
    db_session: AsyncSession,
):
    user = await _make_user(db_session)
    scenario = await _make_master_scenario_with_rows(db_session, user.user_id)
    scenario.mode = "newbie"
    await db_session.flush()
    service = await _make_service(db_session)

    result = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    assert "health" not in result.state
    assert "entities" not in result.state


@pytest.mark.asyncio
async def test_master_snapshot_unchanged(db_session: AsyncSession):
    user = await _make_user(db_session)
    scenario = await _make_master_scenario_with_rows(db_session, user.user_id)

    snapshot = await _start_and_pin(db_session, scenario)

    assert snapshot["mode"] == "master"
    assert snapshot["state_schema"]["health"]["display"] == {"kind": "meter"}
    assert snapshot["enabled_tools"] == ["status_hud", "rule_sheet"]
    assert [e["attributes_schema"] for e in snapshot["entities"]] == [
        MODE_SWITCH_ATTRIBUTES
    ]
    assert len(snapshot["scenario_conditions"]) == 1
    assert len(snapshot["rule_invariants"]) == 1
    assert len(snapshot["end_conditions"]) == 1
    assert len(snapshot["sheet_rules"]) == 1


@pytest.mark.asyncio
async def test_playthrough_keeps_pinned_mode_after_scenario_switch(
    db_session: AsyncSession,
):
    from app.models.scenario import ScenarioUpdate
    from app.services.scenario_service import ScenarioService

    user = await _make_user(db_session)
    scenario = await _make_master_scenario_with_rows(db_session, user.user_id)
    service = await _make_service(db_session)
    started = await service.create_playthrough(
        user_id=user.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )

    await ScenarioService(ScenarioRepo(db_session)).update_scenario(
        scenario.scenario_id, user.user_id, ScenarioUpdate(mode="newbie")
    )
    reloaded = await PlaythroughRepo(db_session).get_by_id(started.playthrough_id)

    assert reloaded.scenario_snapshot["mode"] == "master"
    assert len(reloaded.scenario_snapshot["end_conditions"]) == 1
    assert reloaded.scenario_snapshot["state_schema"]["health"]["initial"] == 7


@pytest.mark.asyncio
async def test_state_overrides_are_refused_outside_a_playtest(
    db_session: AsyncSession,
):
    from app.exceptions.playthrough_exceptions import InvalidStateOverrideError

    user = await _make_user(db_session)
    scenario = await _make_master_scenario_with_rows(db_session, user.user_id)
    service = await _make_service(db_session)

    with pytest.raises(InvalidStateOverrideError):
        await service.create_playthrough(
            user_id=user.user_id,
            data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
            state_overrides={"health": 1},
        )

    assert (
        await PlaythroughRepo(db_session).list_by_scenario(scenario.scenario_id) == []
    )
