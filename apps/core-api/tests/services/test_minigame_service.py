"""Unit/integration tests for MinigameService."""

import uuid

import pytest
from app.db.models.user import User
from app.exceptions.minigame_exceptions import (
    MinigameModeError,
    MinigameNotFoundError,
    MinigameValidationError,
)
from app.models.minigame import (
    DodgeConfig,
    LockpickConfig,
    MinigameCreate,
    MinigameUpdate,
)
from app.models.playthrough import PlaythroughCreate
from app.models.scenario import ScenarioCreate
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
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.share_repo import ShareRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.services.minigame_service import MinigameService
from app.services.playthrough_service import PlaythroughService
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    scenario_service = ScenarioService(ScenarioRepo(db_session))
    return await scenario_service.create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="The Hollow Cairn",
            mode="master",
            complexity_tier="master",
            player_count_support="solo",
            state_schema={
                "player": {"type": "object", "fields": {"health": {"type": "number"}}}
            },
        ),
    )


@pytest.fixture
async def newbie_scenario(db_session: AsyncSession, creator: User):
    scenario_service = ScenarioService(ScenarioRepo(db_session))
    return await scenario_service.create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="A Freeform Tale", mode="newbie", complexity_tier="newbie"
        ),
    )


def _minigame_service(db_session: AsyncSession) -> MinigameService:
    return MinigameService(
        MinigameRepo(db_session),
        EntityRepo(db_session),
        ScenarioRepo(db_session),
    )


def _binary_dodge_create(**overrides) -> MinigameCreate:
    defaults: dict[str, object] = {
        "label": "Warden's Onslaught",
        "minigame_type": "dodge",
        "outcome_mode": "binary",
        "win_mutation": {"path": "player.health", "op": "set", "value": 100},
        "lose_mutation": {"path": "player.health", "op": "decrement", "value": 15},
        "dodge_config": DodgeConfig(difficulty=3),
    }
    defaults.update(overrides)
    return MinigameCreate(**defaults)


def _binary_lockpick_create(**overrides) -> MinigameCreate:
    defaults: dict[str, object] = {
        "label": "The Iron Chest",
        "minigame_type": "lockpick",
        "outcome_mode": "binary",
        "win_mutation": {"path": "player.health", "op": "set", "value": 100},
        "lose_mutation": {"path": "player.health", "op": "decrement", "value": 10},
        "lockpick_config": LockpickConfig(difficulty=3, picks=3),
    }
    defaults.update(overrides)
    return MinigameCreate(**defaults)


@pytest.mark.asyncio
async def test_create_minigame_rejects_newbie_mode_scenario(
    db_session: AsyncSession, newbie_scenario, creator: User
):
    service = _minigame_service(db_session)
    with pytest.raises(MinigameModeError):
        await service.create_minigame(
            newbie_scenario.scenario_id, creator.user_id, _binary_dodge_create()
        )


@pytest.mark.asyncio
async def test_create_minigame_master_mode_succeeds(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )
    assert created.label == "Warden's Onslaught"
    assert created.minigame_type == "dodge"
    assert created.dodge_config == DodgeConfig(difficulty=3)


@pytest.mark.asyncio
async def test_create_lockpick_minigame_master_mode_succeeds(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_lockpick_create()
    )
    assert created.label == "The Iron Chest"
    assert created.minigame_type == "lockpick"
    assert created.lockpick_config is not None
    assert created.lockpick_config.difficulty == 3
    assert created.lockpick_config.picks == 3


@pytest.mark.asyncio
async def test_create_binary_minigame_with_tiered_outcomes_rejected():
    """Pydantic's model_validator on MinigameCreate itself rejects a binary
    outcome_mode carrying tiered_outcomes — the single source of truth for
    outcome-shape validation, exercised again at the router layer in
    test_minigame_router.py."""
    with pytest.raises(ValueError):
        _binary_dodge_create(
            tiered_outcomes=[
                {
                    "min_score": 0,
                    "max_score": 10,
                    "mutation": {"path": "player.health", "op": "set", "value": 0},
                }
            ]
        )


@pytest.mark.asyncio
async def test_create_tiered_minigame_without_outcomes_rejected():
    with pytest.raises(ValueError):
        _binary_dodge_create(
            outcome_mode="tiered",
            win_mutation=None,
            lose_mutation=None,
            tiered_outcomes=[],
        )


@pytest.mark.asyncio
async def test_trigger_expression_unknown_field_rejected(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    data = _binary_dodge_create(
        trigger_condition_expression={
            "field": "not_a_real_field",
            "op": "==",
            "value": True,
        }
    )
    with pytest.raises(MinigameValidationError):
        await service.create_minigame(
            master_scenario.scenario_id, creator.user_id, data
        )


@pytest.mark.asyncio
async def test_list_minigames_ordered_by_priority_ascending(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    await service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="Third", priority=5),
    )
    await service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="First", priority=1),
    )
    await service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="Second", priority=3),
    )

    items = await service.list_minigames(master_scenario.scenario_id, creator.user_id)
    assert [i.label for i in items] == ["First", "Second", "Third"]


@pytest.mark.asyncio
async def test_reorder_minigames(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    first = await service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="A", priority=0),
    )
    second = await service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="B", priority=1),
    )

    reordered = await service.reorder_minigames(
        master_scenario.scenario_id,
        creator.user_id,
        [second.minigame_id, first.minigame_id],
    )
    assert [m.minigame_id for m in reordered] == [second.minigame_id, first.minigame_id]
    assert reordered[0].priority == 0
    assert reordered[1].priority == 1


@pytest.mark.asyncio
async def test_delete_minigame(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )
    await service.delete_minigame(
        master_scenario.scenario_id, created.minigame_id, creator.user_id
    )
    with pytest.raises(MinigameNotFoundError):
        await service.get_minigame(
            master_scenario.scenario_id, created.minigame_id, creator.user_id
        )


@pytest.mark.asyncio
async def test_update_minigame_reintroducing_invalid_shape_rejected(
    db_session: AsyncSession, master_scenario, creator: User
):
    """A PATCH that would leave the merged minigame shape invalid (binary outcome
    carrying tiered_outcomes) is rejected the same way a create would be."""
    from app.models.minigame import MinigameUpdate

    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )
    with pytest.raises(MinigameValidationError):
        await service.update_minigame(
            master_scenario.scenario_id,
            created.minigame_id,
            creator.user_id,
            MinigameUpdate(
                tiered_outcomes=[
                    {
                        "min_score": 0,
                        "max_score": 10,
                        "mutation": {"path": "player.health", "op": "set", "value": 0},
                    }
                ]
            ),
        )


@pytest.mark.asyncio
async def test_playthrough_snapshot_includes_minigames_sorted_by_priority(
    db_session: AsyncSession, master_scenario, creator: User
):
    """Task 3 verification: creating a playthrough for a scenario with 2
    minigames produces scenario_snapshot["scenario_minigames"] sorted by
    priority ascending."""
    minigame_service = _minigame_service(db_session)
    await minigame_service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="Second", priority=4),
    )
    await minigame_service.create_minigame(
        master_scenario.scenario_id,
        creator.user_id,
        _binary_dodge_create(label="First", priority=1),
    )

    playthrough_service = PlaythroughService(
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
    result = await playthrough_service.create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(
            scenario_id=master_scenario.scenario_id, setup_values={}
        ),
        is_playtest=True,
    )

    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    minigames = stored.scenario_snapshot["scenario_minigames"]
    assert [m["label"] for m in minigames] == ["First", "Second"]
    assert minigames[0]["outcome_mode"] == "binary"
    assert minigames[0]["dodge_config"]["difficulty"] == 3


@pytest.mark.asyncio
async def test_playthrough_snapshot_carries_validated_lockpick_config(
    db_session: AsyncSession, master_scenario, creator: User
):
    await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_lockpick_create()
    )
    playthrough_service = PlaythroughService(
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

    result = await playthrough_service.create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(
            scenario_id=master_scenario.scenario_id, setup_values={}
        ),
        is_playtest=True,
    )

    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    snapshot_minigame = stored.scenario_snapshot["scenario_minigames"][0]
    assert snapshot_minigame["lockpick_config"] == LockpickConfig(
        difficulty=3, picks=3
    ).model_dump(mode="json")


def _mutation(path: str, value: object, op: str = "set") -> dict[str, object]:
    return {"path": path, "op": op, "value": value}


def _listed_dodge_create(**overrides) -> MinigameCreate:
    return _binary_dodge_create(
        win_mutation=None,
        lose_mutation=None,
        win_mutations=[
            _mutation("player.health", 100),
            _mutation("player.health", 90),
        ],
        lose_mutations=[_mutation("player.health", 10, "decrement")],
        **overrides,
    )


@pytest.mark.asyncio
async def test_outcome_mutation_lists_round_trip_in_order(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)

    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _listed_dodge_create()
    )

    assert [m.value for m in created.win_mutations] == [100, 90]
    assert created.win_mutation.value == 100
    assert [m.op for m in created.lose_mutations] == ["decrement"]
    assert created.timeout_mutations == []


@pytest.mark.asyncio
async def test_legacy_single_outcome_mutations_are_folded_into_lists(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)

    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )
    stored = await MinigameRepo(db_session).get_by_id(created.minigame_id)

    assert stored.win_mutation is None
    assert stored.win_mutations == [_mutation("player.health", 100)]
    assert stored.lose_mutations == [_mutation("player.health", 15, "decrement")]
    assert created.win_mutation.value == 100


def test_binary_outcome_accepts_lists_without_legacy_singles():
    assert _listed_dodge_create().outcome_mode == "binary"


def test_binary_outcome_still_requires_a_win_mutation_in_some_shape():
    with pytest.raises(ValueError):
        _binary_dodge_create(win_mutation=None, win_mutations=[])


def test_outcome_list_rejects_more_than_the_cap():
    with pytest.raises(ValueError):
        _listed_dodge_create(timeout_mutations=[_mutation("player.health", 1)] * 17)


def test_outcome_rejects_both_single_and_list_for_the_same_slot():
    with pytest.raises(ValueError):
        _binary_dodge_create(win_mutations=[_mutation("player.health", 1)])


@pytest.mark.asyncio
async def test_update_with_legacy_single_replaces_an_existing_list(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _listed_dodge_create()
    )

    updated = await service.update_minigame(
        master_scenario.scenario_id,
        created.minigame_id,
        creator.user_id,
        MinigameUpdate(win_mutation=_mutation("player.health", 55)),
    )

    assert [m.value for m in updated.win_mutations] == [55]


@pytest.mark.asyncio
async def test_duplicate_preserves_outcome_mutation_lists(
    db_session: AsyncSession, master_scenario, creator: User
):
    await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _listed_dodge_create()
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await MinigameRepo(db_session).list_by_scenario(copy.scenario_id)

    assert [m["value"] for m in copied[0].win_mutations] == [100, 90]
    assert [m["op"] for m in copied[0].lose_mutations] == ["decrement"]


@pytest.mark.asyncio
async def test_duplicate_preserves_lockpick_config(
    db_session: AsyncSession, master_scenario, creator: User
):
    await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_lockpick_create()
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await MinigameRepo(db_session).list_by_scenario(copy.scenario_id)

    assert copied[0].lockpick_config["picks"] == 3


@pytest.mark.asyncio
async def test_outcome_list_with_undeclared_nested_path_is_rejected(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)

    with pytest.raises(MinigameValidationError):
        await service.create_minigame(
            master_scenario.scenario_id,
            creator.user_id,
            _binary_dodge_create(
                win_mutation=None,
                win_mutations=[_mutation("player.nope", 1)],
            ),
        )


@pytest.mark.asyncio
async def test_outcome_list_with_declared_path_is_accepted(
    db_session: AsyncSession, master_scenario, creator: User
):
    created = await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _listed_dodge_create()
    )

    assert created.win_mutations[0].path == "player.health"


@pytest.mark.asyncio
async def test_update_validates_new_outcome_list_paths(
    db_session: AsyncSession, master_scenario, creator: User
):
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )

    with pytest.raises(MinigameValidationError):
        await service.update_minigame(
            master_scenario.scenario_id,
            created.minigame_id,
            creator.user_id,
            MinigameUpdate(lose_mutations=[_mutation("player.nope", 1)]),
        )


async def _enable_tool(db_session, scenario_id, creator, tools):
    from app.models.tools import ToolsUpdate
    from app.services.tool_service import ToolService
    from app.tools.data_counters import count_tool_rows

    async def count_rows(tool_key: str, owned_scenario_id: uuid.UUID) -> int:
        return await count_tool_rows(db_session, tool_key, owned_scenario_id)

    await ToolService(ScenarioRepo(db_session), count_rows).update_tools(
        scenario_id, creator.user_id, ToolsUpdate(enabled_tools=tools)
    )


def _composure_create(**overrides) -> MinigameCreate:
    from app.models.minigame import ComposureConfig

    defaults: dict[str, object] = {
        "label": "The stairwell hum",
        "minigame_type": "rhythm_composure",
        "outcome_mode": "binary",
        "win_mutations": [{"path": "player.health", "op": "increment", "value": 5}],
        "lose_mutations": [{"path": "player.health", "op": "decrement", "value": 20}],
        "composure_config": ComposureConfig(target_bpm=60),
    }
    defaults.update(overrides)
    return MinigameCreate(**defaults)


async def test_composure_minigame_needs_the_composure_tool(
    db_session, creator, master_scenario
):
    from app.exceptions.tool_exceptions import ToolNotEnabledError

    service = _minigame_service(db_session)

    with pytest.raises(ToolNotEnabledError) as raised:
        await service.create_minigame(
            master_scenario.scenario_id, creator.user_id, _composure_create()
        )

    assert raised.value.tool_key == "composure"


async def test_composure_minigame_round_trips_with_the_tool_on(
    db_session, creator, master_scenario
):
    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    service = _minigame_service(db_session)

    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )
    fetched = await service.get_minigame(
        master_scenario.scenario_id, created.minigame_id, creator.user_id
    )

    assert fetched.composure_config.target_bpm == 60
    assert fetched.minigame_type == "rhythm_composure"


async def test_other_minigame_types_never_need_the_tool(
    db_session, creator, master_scenario
):
    service = _minigame_service(db_session)

    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )

    assert created.minigame_type == "dodge"


async def test_composure_update_revalidates_and_stays_gated(
    db_session, creator, master_scenario
):
    from app.exceptions.tool_exceptions import ToolNotEnabledError
    from app.models.minigame import ComposureConfig

    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    service = _minigame_service(db_session)
    created = await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )

    updated = await service.update_minigame(
        master_scenario.scenario_id,
        created.minigame_id,
        creator.user_id,
        MinigameUpdate(composure_config=ComposureConfig(max_strikes=4)),
    )
    await _enable_tool(db_session, master_scenario.scenario_id, creator, [])
    with pytest.raises(ToolNotEnabledError):
        await service.update_minigame(
            master_scenario.scenario_id,
            created.minigame_id,
            creator.user_id,
            MinigameUpdate(label="renamed"),
        )

    assert updated.composure_config.max_strikes == 4


async def _start(db_session, creator, scenario_id):
    scenario = await ScenarioRepo(db_session).get_by_id(scenario_id)
    scenario.status = "published"
    await db_session.flush()
    from tests.services.test_tool_snapshot import _make_service

    return await _make_service(db_session).create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(scenario_id=scenario_id, setup_values={}),
    )


async def test_snapshot_carries_composure_config_when_the_tool_is_on(
    db_session, creator, master_scenario
):
    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    pinned = stored.scenario_snapshot["scenario_minigames"][0]

    assert pinned["composure_config"]["target_bpm"] == 60
    assert pinned["composure_config"]["beats_to_win"] == 5
    assert pinned["composure_config"]["keys"] == ["W", "A", "S", "D"]


async def test_snapshot_omits_composure_rows_when_the_tool_is_off(
    db_session, creator, master_scenario
):
    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    service = _minigame_service(db_session)
    await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )
    await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )
    await _enable_tool(db_session, master_scenario.scenario_id, creator, [])

    result = await _start(db_session, creator, master_scenario.scenario_id)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    pinned = stored.scenario_snapshot["scenario_minigames"]

    assert [m["minigame_type"] for m in pinned] == ["dodge"]


async def test_duplicate_preserves_composure_config(
    db_session, creator, master_scenario
):
    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    await _minigame_service(db_session).create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        master_scenario.scenario_id, creator.user_id
    )
    copied = await MinigameRepo(db_session).list_by_scenario(copy.scenario_id)

    assert copied[0].composure_config["target_bpm"] == 60


async def test_inert_count_reports_composure_rows_of_a_disabled_tool(
    db_session, creator, master_scenario
):
    from app.tools.data_counters import count_tool_rows

    await _enable_tool(db_session, master_scenario.scenario_id, creator, ["composure"])
    service = _minigame_service(db_session)
    await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _composure_create()
    )
    await service.create_minigame(
        master_scenario.scenario_id, creator.user_id, _binary_dodge_create()
    )

    count = await count_tool_rows(db_session, "composure", master_scenario.scenario_id)

    assert count == 1
