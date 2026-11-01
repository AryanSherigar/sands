from uuid import uuid4

from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.models.stance import (
    StanceBriefing,
    StanceChoice,
    StanceRequest,
    StanceSource,
)
from app.models.world_character import LeaderState
from app.repositories import (
    replay_step_repo,
    stance_request_repo,
    world_snapshot_repo,
    world_state_repo,
)
from app.services.campaign_service import CampaignService
from app.services.world_view_service import WorldViewService
from psycopg import AsyncConnection
from pytest import MonkeyPatch
from tests.engine.economy.builders import RIVAL, make_scenario
from tests.engine.economy.test_shortfall import _world as shortfall_world
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation, seed_world
from tests.services.stance_fixtures import ready_settings
from tests.services.test_campaign_service import guard, initialization

SELECT_REQUESTS = "SELECT leader_id, due_turn, state FROM stance_requests ORDER BY due_turn, leader_id"


def _turn_guard(operation_id: str, version: int, turn: int):
    return guard(operation_id, version).model_copy(update={"expected_turn": turn})


async def _requests(connection: AsyncConnection) -> list[tuple[str, int, str]]:
    cursor = await connection.execute(SELECT_REQUESTS)
    return await cursor.fetchall()


async def _world(connection: AsyncConnection, playthrough_id):
    row = await world_state_repo.get_world_state(connection, playthrough_id)
    return world_from_document(row.document)


async def _two_turns(connection: AsyncConnection, between=None):
    request = initialization()
    service = CampaignService(connection)
    await service.initialize(request)
    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin1", 1))
    if between is not None:
        await between(request.playthrough_id)
    await service.begin(
        request.playthrough_id, OWNER_USER_ID, _turn_guard("begin2", 2, 1)
    )
    return request


def _model_choice(due_turn: int = 2) -> StanceChoice:
    return StanceChoice(
        leader_id="mira",
        faction_id="house_ashford",
        due_turn=due_turn,
        option_id="expand",
        source=StanceSource.MODEL,
        reason_code="model_pick",
        input_hash="hash-model",
    )


async def test_completing_a_turn_schedules_next_turns_stance_requests(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    service = CampaignService(db_connection)
    await service.initialize(request)
    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin1", 1))
    assert await _requests(db_connection) == [
        ("harl", 2, "fallback"),
        ("mira", 2, "fallback"),
    ]


async def test_next_turn_applies_each_stance_once_and_seals_requests(
    db_connection: AsyncConnection,
) -> None:
    request = await _two_turns(db_connection)
    world = await _world(db_connection, request.playthrough_id)
    stance = world.factions["house_ashford"].stance
    assert world.clock.turn == 2
    assert (stance.option_id is not None, stance.chosen_turn) == (True, 2)
    assert {row[2] for row in await _requests(db_connection)} == {"activated"}
    assert len(await _requests(db_connection)) == 2


async def test_model_answer_before_the_due_turn_is_applied(
    db_connection: AsyncConnection, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.campaign_service.get_settings", lambda: ready_settings()
    )

    async def answer(playthrough_id) -> None:
        claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
        mira = next(item for item in claimed if item.leader_id == "mira")
        assert await stance_request_repo.complete_request(
            db_connection,
            playthrough_id,
            mira.request_id,
            mira.lease_token,
            _model_choice().model_copy(update={"input_hash": mira.input_hash}),
        )

    request = await _two_turns(db_connection, between=answer)
    world = await _world(db_connection, request.playthrough_id)
    assert world.factions["house_ashford"].stance.option_id == "expand"
    assert world.factions["house_dunwick"].stance.option_id is not None


async def test_unanswered_request_applies_fallback_and_late_answer_is_dropped(
    db_connection: AsyncConnection, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.campaign_service.get_settings", lambda: ready_settings()
    )
    claimed: list = []

    async def lease_only(playthrough_id) -> None:
        claimed.extend(
            await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
        )

    request = await _two_turns(db_connection, between=lease_only)
    world = await _world(db_connection, request.playthrough_id)
    applied = world.factions["house_ashford"].stance.option_id
    mira = next(item for item in claimed if item.leader_id == "mira")
    was_recorded = await stance_request_repo.complete_request(
        db_connection,
        request.playthrough_id,
        mira.request_id,
        mira.lease_token,
        _model_choice().model_copy(update={"input_hash": mira.input_hash}),
    )
    assert was_recorded is False
    after = await _world(db_connection, request.playthrough_id)
    assert after.factions["house_ashford"].stance.option_id == applied


async def test_replay_of_recorded_history_reproduces_world_hash(
    db_connection: AsyncConnection,
) -> None:
    request = await _two_turns(db_connection)
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    result = replay_history(
        world_from_document(snapshot.document), request.scenario, steps
    )
    assert result.world_hash == steps[-1].after_hash
    assert steps[-1].input.stances
    assert not steps[0].input.stances


async def test_resume_economy_completing_a_turn_applies_stance_exactly_once(
    db_connection: AsyncConnection,
) -> None:
    world = shortfall_world()
    world.leaders = {
        "rival_lord": LeaderState(
            id="rival_lord", name="Rival", faction_id=RIVAL, age=40
        )
    }
    world.factions[RIVAL].leader_id = "rival_lord"
    identity = await seed_world(db_connection, world, make_scenario())
    choice = _model_choice(1).model_copy(
        update={"leader_id": "rival_lord", "faction_id": RIVAL}
    )
    await stance_request_repo.insert_request(
        db_connection, _request_for(identity, choice)
    )
    leased = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    assert await stance_request_repo.complete_request(
        db_connection, identity, leased[0].request_id, leased[0].lease_token, choice
    )
    service = CampaignService(db_connection)
    paused = await service.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    assert (await _world(db_connection, identity)).factions[
        RIVAL
    ].stance.option_id is None
    request = mutation("choice", paused.world_version)
    for _ in range(2):
        await service.resume_economy(
            identity, OWNER_USER_ID, request, paused.scene_id, "shortfall_default"
        )
    stance = (await _world(db_connection, identity)).factions[RIVAL].stance
    assert (stance.option_id, stance.chosen_turn) == ("expand", 1)


async def test_stance_never_appears_in_client_views(
    db_connection: AsyncConnection,
) -> None:
    request = await _two_turns(db_connection)
    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )
    dumped = view.model_dump_json().lower()
    assert "stance" not in dumped
    assert "revenge_on_player" not in dumped


def _request_for(identity, choice: StanceChoice) -> StanceRequest:
    return StanceRequest(
        playthrough_id=identity,
        request_id=f"stance:{choice.leader_id}:{choice.due_turn}",
        leader_id=choice.leader_id,
        faction_id=choice.faction_id,
        due_turn=choice.due_turn,
        input_hash=choice.input_hash,
        briefing=StanceBriefing(
            leader_name="Rival",
            trait_notes=[],
            ambitions=[],
            memories=[],
            opinions=[],
            current_option_id=None,
            menu=[],
        ),
        fallback=choice.model_copy(
            update={"source": StanceSource.FALLBACK, "option_id": "turtle"}
        ),
    )
