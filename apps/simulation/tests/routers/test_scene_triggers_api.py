from httpx import AsyncClient
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator
from strategy_contracts.negotiation_rules import NegotiationRules, NegotiationTrigger
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

INTERNAL = {"X-Internal-Service-Token": "internal"}
RIVAL = "house_ashford"
FIRST_PLANNED_TURN = 1
COOLDOWN_TURNS = 5


async def _start_with_trigger(api: AsyncClient, is_declinable: bool) -> tuple[str, int]:
    request = initialization()
    request.scenario.negotiation = NegotiationRules(
        triggers=[
            NegotiationTrigger(
                id="ashford_offer",
                initiator_faction_id=RIVAL,
                condition=Comparison(
                    metric=ConditionMetric.TURN,
                    operator=ConditionOperator.GTE,
                    value=FIRST_PLANNED_TURN,
                ),
                is_declinable=is_declinable,
                cooldown_turns=COOLDOWN_TURNS,
            )
        ]
    )
    body = request.model_dump(mode="json")
    created = await api.post("/internal/v1/playthroughs", json=body, headers=INTERNAL)
    return f"/v1/playthroughs/{body['playthrough_id']}", created.json()["world_version"]


async def _end_turn_into_offer(
    api: AsyncClient, is_declinable: bool
) -> tuple[str, dict, str]:
    base, version = await _start_with_trigger(api, is_declinable)
    ended = await api.post(
        f"{base}/end-turn", json=mutation("end", version).model_dump()
    )
    assert ended.status_code == 200
    world = (await api.get(f"{base}/world")).json()
    assert world["status"] == "awaiting_scene"
    return base, world, world["scene_id"]


def _decision(operation: str, world: dict, is_confirmed: bool) -> dict:
    return mutation(operation, world["world_version"], world["turn"]).model_dump() | {
        "is_confirmed": is_confirmed
    }


async def test_turn_rollover_opens_a_rival_offer_the_player_can_decline(
    api: AsyncClient,
) -> None:
    base, world, scene_id = await _end_turn_into_offer(api, is_declinable=True)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["initiator"], view["is_declinable"]) == ("ai", True)
    blocked = await api.post(
        f"{base}/end-turn",
        json=mutation("end-again", world["world_version"], world["turn"]).model_dump(),
    )
    assert (blocked.status_code, blocked.json()["code"]) == (409, "scene_pending")
    declined = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False),
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "planning"


async def test_a_declined_offer_does_not_return_during_its_cooldown(
    api: AsyncClient,
) -> None:
    base, world, scene_id = await _end_turn_into_offer(api, is_declinable=True)
    declined = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False),
    )
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation(
            "next", declined.json()["world_version"], declined.json()["turn"]
        ).model_dump(),
    )
    assert ended.status_code == 200
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_a_forced_offer_cannot_be_declined_but_the_leader_can_end_it(
    api: AsyncClient,
) -> None:
    base, world, scene_id = await _end_turn_into_offer(api, is_declinable=False)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["is_declinable"] is False
    refused = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False),
    )
    assert (refused.status_code, refused.json()["code"]) == (422, "not_declinable")
    path = f"/internal/v1/scenes/{scene_id}"
    headers = INTERNAL | {"X-Acting-User-Id": str(OWNER_USER_ID)}
    exchange = {
        "sequence": 1,
        "player_text": "Hear me out",
        "leader_text": "No.",
        "decision": {"action": "refuse", "duration_turns": None},
    }
    ended = await api.post(f"{path}/exchanges", json=exchange, headers=headers)
    assert ended.json()["scene_status"] == "resolved"
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_replay_verification_passes_across_a_triggered_offer(
    api: AsyncClient,
) -> None:
    base, world, scene_id = await _end_turn_into_offer(api, is_declinable=True)
    await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=_decision("decline", world, False),
    )
    verified = await api.post(f"{base}/replay/verify")
    assert verified.status_code == 200
