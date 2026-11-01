from httpx import AsyncClient
from strategy_contracts.examples import load_three_crowns
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}
PLAYER_FACTION = "house_carrow"
RAISE_TAX = {"kind": "set_tax_rate", "faction_id": PLAYER_FACTION, "tax_rate": "high"}


def guard(operation_id: str, version: int) -> dict[str, object]:
    return {
        "operation_id": operation_id,
        "expected_world_version": version,
        "expected_turn": 0,
        "expected_wave": 0,
    }


async def start(api: AsyncClient) -> tuple[str, int]:
    request = initialization().model_dump(mode="json")
    created = await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    return f"/v1/playthroughs/{request['playthrough_id']}", created.json()[
        "world_version"
    ]


async def test_check_reports_a_flag_and_changes_nothing(api: AsyncClient) -> None:
    base, version = await start(api)
    levy = {
        "kind": "raise_army",
        "faction_id": PLAYER_FACTION,
        "region_id": "unknown_region",
        "troops": {"infantry": 10},
    }
    flagged = await api.post(f"{base}/commands/check", json={"command": levy})
    assert flagged.status_code == 200
    assert flagged.json()["flag"] is not None
    ok = await api.post(f"{base}/commands/check", json={"command": RAISE_TAX})
    assert ok.status_code == 200
    assert ok.json()["flag"] is None
    world = (await api.get(f"{base}/world")).json()
    assert world["world_version"] == version
    assert world["queued_orders"] == []


async def test_order_bar_lists_queued_orders_and_cancel_empties_it(
    api: AsyncClient,
) -> None:
    base, version = await start(api)
    start_points = (await api.get(f"{base}/world")).json()["orders_remaining"]
    accepted = await api.post(
        f"{base}/commands", json=guard("tax", version) | {"command": RAISE_TAX}
    )
    world = (await api.get(f"{base}/world")).json()
    [queued] = world["queued_orders"]
    assert queued["id"] == accepted.json()["accepted_command_id"]
    assert queued["is_cancellable"] is True
    assert world["orders_remaining"] < start_points
    cancelled = await api.post(
        f"{base}/commands/{queued['id']}/cancel",
        json=guard("untax", accepted.json()["world_version"]),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["orders_remaining"] == start_points
    assert (await api.get(f"{base}/world")).json()["queued_orders"] == []
    assert (await api.get(f"{base}/commands")).json()["items"] == []


async def test_cancelling_an_unknown_order_is_a_404(api: AsyncClient) -> None:
    base, version = await start(api)
    response = await api.post(
        f"{base}/commands/missing/cancel", json=guard("untax", version)
    )
    assert response.status_code == 404


def _besiege_order(target_region_id: str) -> dict[str, object]:
    scenario = load_three_crowns()
    army = next(
        item for item in scenario.starting.armies if item.owner_id == PLAYER_FACTION
    )
    return {
        "kind": "besiege",
        "faction_id": PLAYER_FACTION,
        "army_id": army.id,
        "target_region_id": target_region_id,
    }


def _army_region() -> str:
    scenario = load_three_crowns()
    return next(
        item.location_id
        for item in scenario.starting.armies
        if item.owner_id == PLAYER_FACTION
    )


async def test_check_flags_besieging_your_own_region(api: AsyncClient) -> None:
    base, _ = await start(api)

    response = await api.post(
        f"{base}/commands/check", json={"command": _besiege_order(_army_region())}
    )

    assert response.status_code == 200
    assert response.json()["flag"] == "impossible"
    assert response.json()["reason"] == "own_region"


async def test_accepting_a_besiege_order_for_the_wrong_region_is_refused(
    api: AsyncClient,
) -> None:
    base, version = await start(api)
    elsewhere = next(
        region.id
        for region in load_three_crowns().map.regions
        if region.id != _army_region()
    )

    response = await api.post(
        f"{base}/commands",
        json=guard("besiege", version) | {"command": _besiege_order(elsewhere)},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "wrong_region"
