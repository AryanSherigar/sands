from app.models.world_events import PendingEvent
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.scenario import StrategyScenario
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)
from tests.services.helpers import mutation, seed_world

EVENT_ID = "event_1"
EASE_COST = 1
BASE_TREASURY = 500
STARTING_ORDERS = 6


def _answer(choice_id: str = "ease_taxes") -> dict[str, object]:
    return {
        "kind": "answer_event",
        "faction_id": PLAYER,
        "event_id": EVENT_ID,
        "choice_id": choice_id,
    }


async def _seed(db_connection: AsyncConnection, orders: int = STARTING_ORDERS) -> str:
    faction = make_faction(PLAYER, is_player=True)
    faction.treasury = BASE_TREASURY
    faction.orders_remaining = orders
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=70)], factions=[faction]
    )
    world.events_ruleset = 1
    world.pending_events = [
        PendingEvent(
            id=EVENT_ID,
            template_id="tax_grievance",
            choice_ids=["ease_taxes", "garrison_crackdown"],
            subject_kind=ConditionScope.REGION,
            subject_id=HOME,
            subject_name="Home",
            tier=1,
            created_turn=0,
            deadline_turn=0,
            cause_key="tax_grievance",
            cause_inputs={"region_unrest": 70},
        )
    ]
    identity = await seed_world(db_connection, world, StrategyScenario())
    return f"/v1/playthroughs/{identity}"


async def test_answering_an_event_is_a_charged_idempotent_order(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    before = STARTING_ORDERS
    payload = mutation("answer", 1).model_dump() | {"command": _answer()}

    first = await api.post(f"{base}/commands", json=payload)
    second = await api.post(f"{base}/commands", json=payload)

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert first.json()["orders_remaining"] == before - EASE_COST
    [queued] = (await api.get(f"{base}/commands")).json()["items"]
    assert queued["id"] == first.json()["accepted_command_id"]


async def test_cancelling_the_answer_refunds_its_cost(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    before = STARTING_ORDERS
    accepted = await api.post(
        f"{base}/commands",
        json=mutation("answer", 1).model_dump() | {"command": _answer()},
    )
    cancelled = await api.post(
        f"{base}/commands/{accepted.json()['accepted_command_id']}/cancel",
        json=mutation("undo", accepted.json()["world_version"]).model_dump(),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["orders_remaining"] == before


async def test_an_unaffordable_answer_is_flagged_and_refused(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection, orders=0)
    check = await api.post(f"{base}/commands/check", json={"command": _answer()})
    assert check.json()["flag"] == "over_budget"
    refused = await api.post(
        f"{base}/commands",
        json=mutation("answer", 1).model_dump() | {"command": _answer()},
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "insufficient_points"


async def test_an_unknown_event_is_a_404(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seed(db_connection)
    command = _answer() | {"event_id": "event_404"}
    response = await api.post(
        f"{base}/commands",
        json=mutation("answer", 1).model_dump() | {"command": command},
    )
    assert response.status_code == 404
