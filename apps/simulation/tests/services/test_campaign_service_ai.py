from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.repositories import event_log_repo, replay_step_repo, world_snapshot_repo
from app.services.campaign_service import CampaignService
from app.services.world_view_service import WorldViewService
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization

TURNS = 3
HIDDEN_MARKERS = (
    "ai_order",
    "ai_aim",
    "ai_ruleset",
    '"aims"',
    "npc:",
    "trait_score",
    "stance_score",
    "aim_score",
)
AI_STANCE = "turtle"


def _turtle_initialization():
    request = initialization()
    for faction in request.scenario.factions:
        if faction.id != request.player_faction_id:
            faction.stance_ids = [AI_STANCE]
    return request


async def _play_turns(connection: AsyncConnection, turns: int):
    request = _turtle_initialization()
    service = CampaignService(connection)
    await service.initialize(request)
    for turn in range(turns):
        step = guard(f"begin{turn}", turn + 1).model_copy(
            update={"expected_turn": turn}
        )
        await service.begin(request.playthrough_id, OWNER_USER_ID, step)
    return request


async def test_ai_factions_plan_orders_and_follow_their_stance_once_active(
    db_connection: AsyncConnection,
) -> None:
    request = await _play_turns(db_connection, TURNS)

    events = await event_log_repo.list_events(db_connection, request.playthrough_id)

    planned = [event for event in events if event.kind == "ai_order_planned"]
    assert planned
    assert all(event.cause.summary_key.startswith("ai_") for event in planned)
    stance_turn_keys = [
        event.cause.summary_key for event in planned if event.turn == TURNS - 1
    ]
    assert any(key.startswith("ai_hoard") for key in stance_turn_keys)


async def test_ai_factions_log_the_aim_they_hold(
    db_connection: AsyncConnection,
) -> None:
    request = await _play_turns(db_connection, TURNS)

    events = await event_log_repo.list_events(db_connection, request.playthrough_id)

    aim_events = [event for event in events if event.kind == "ai_aim_set"]
    assert aim_events
    assert all(event.cause.summary_key.startswith("ai_aim_") for event in aim_events)


async def test_ai_tax_policy_follows_the_stance_in_the_final_world(
    db_connection: AsyncConnection,
) -> None:
    request = await _play_turns(db_connection, TURNS)
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, TURNS
    )
    world = world_from_document(snapshot.document)

    ai_rates = {
        faction.tax_rate for faction in world.factions.values() if not faction.is_player
    }

    assert ai_rates == {TaxRate.HIGH}


async def test_player_world_view_has_no_ai_reasons_or_scores(
    db_connection: AsyncConnection,
) -> None:
    request = await _play_turns(db_connection, TURNS)
    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )

    dumped = view.model_dump_json().lower()

    for marker in HIDDEN_MARKERS:
        assert marker not in dumped


async def test_replay_of_ai_planned_turns_reproduces_world_hash(
    db_connection: AsyncConnection,
) -> None:
    request = await _play_turns(db_connection, TURNS)
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)

    result = replay_history(
        world_from_document(snapshot.document), request.scenario, steps
    )

    assert len(steps) == TURNS
    assert result.world_hash == steps[-1].after_hash
