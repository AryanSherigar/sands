"""End-to-end probing script for the deterministic strategy simulation service."""

import asyncio
import os
import sys
import time
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
import jwt
from app.config import get_settings
from app.db.pool import get_connection
from app.main import create_app
from app.models.orders import SetTaxRateOrder
from app.models.world_state import WorldState
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scenario import StrategyScenario
from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    make_army,
    make_faction,
    make_region,
    make_scenario,
    make_world,
)
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import seed_battle, seed_world

SHARED_SECRET = "probe-secret-key-that-is-at-least-32-bytes-long"
INTERNAL_TOKEN = "internal-probe-service-token"


def make_auth_header(user_id: UUID) -> dict[str, str]:
    claims = {
        "sub": str(user_id),
        "type": "access",
        "token_version": 1,
        "exp": int(time.time()) + 3600,
    }
    encoded = jwt.encode(claims, SHARED_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {encoded}"}


def make_internal_header() -> dict[str, str]:
    return {"X-Internal-Service-Token": INTERNAL_TOKEN}


def log_step(name: str, detail: str) -> None:
    print(f"\033[1;36m[STEP]\033[0m \033[1m{name}\033[0m: {detail}")


def log_success(detail: str) -> None:
    print(f"  \033[1;32m✓\033[0m {detail}")


def make_shortfall_world() -> tuple[WorldState, StrategyScenario]:
    wealth = 50
    regions = [make_region("home", PLAYER, wealth=wealth)]
    factions = [
        make_faction(PLAYER, treasury=0, is_player=True),
        make_faction(RIVAL),
    ]
    armies = [
        make_army("army_a", PLAYER, troops={"infantry": 400}),
        make_army("army_b", PLAYER, troops={"infantry": 800}),
    ]
    world = make_world(regions=regions, factions=factions, armies=armies)
    return world, make_scenario()


async def _init_campaign(api: httpx.AsyncClient) -> tuple[UUID, int]:
    log_step(
        "1. Initialization",
        "Initializing Three Crowns campaign via /internal/v1/playthroughs",
    )
    playthrough_id = uuid4()
    init_payload = {
        "playthrough_id": str(playthrough_id),
        "owner_user_id": str(OWNER_USER_ID),
        "operation_id": "probe_init_1",
        "scenario": load_three_crowns().model_dump(mode="json"),
        "seed": 42,
        "player_faction_id": "house_carrow",
        "ruler": make_world().ruler.model_dump(mode="json"),
    }
    response = await api.post(
        "/internal/v1/playthroughs",
        json=init_payload,
        headers=make_internal_header(),
    )
    assert response.status_code == 200, f"Init failed: {response.text}"
    version = response.json()["world_version"]
    log_success(
        f"Campaign created: playthrough_id={playthrough_id}, world_version={version}"
    )
    return playthrough_id, version


async def _check_world_view(api: httpx.AsyncClient, playthrough_id: UUID) -> None:
    log_step("2. World Fog View", "Querying /v1/playthroughs/{id}/world")
    world_res = await api.get(f"/v1/playthroughs/{playthrough_id}/world")
    assert world_res.status_code == 200, f"World view failed: {world_res.text}"
    world_data = world_res.json()
    assert "manpower_pool" not in world_res.text, "Leaked hidden manpower_pool!"
    assert "rng" not in world_res.text, "Leaked engine RNG state!"
    log_success(
        f"Turn={world_data['clock']['turn']}, Player faction={world_data['my_faction']['id']}"
    )


async def _submit_tax_command(
    api: httpx.AsyncClient, playthrough_id: UUID, version: int
) -> int:
    log_step(
        "3. Issue Order",
        "Submitting SetTaxRateOrder (high tax) via /v1/playthroughs/{id}/commands",
    )
    tax_order = SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH)
    cmd_payload = {
        "operation_id": "probe_cmd_tax",
        "expected_world_version": version,
        "expected_turn": 0,
        "expected_wave": 0,
        "command": tax_order.model_dump(mode="json"),
    }
    cmd_res = await api.post(
        f"/v1/playthroughs/{playthrough_id}/commands", json=cmd_payload
    )
    assert cmd_res.status_code == 200, f"Command failed: {cmd_res.text}"
    new_version = cmd_res.json()["world_version"]
    log_success(f"Tax command accepted! New world_version={new_version}")
    return new_version


async def _advance_turn(
    api: httpx.AsyncClient, playthrough_id: UUID, version: int
) -> tuple[int, int]:
    log_step("4. Advance Campaign Turn", "Calling /v1/playthroughs/{id}/end-turn")
    end_turn_payload = {
        "operation_id": "probe_end_turn_0",
        "expected_world_version": version,
        "expected_turn": 0,
        "expected_wave": 0,
    }
    turn_res = await api.post(
        f"/v1/playthroughs/{playthrough_id}/end-turn", json=end_turn_payload
    )
    assert turn_res.status_code == 200, f"End turn failed: {turn_res.text}"
    new_version = turn_res.json()["world_version"]
    turn_num = turn_res.json()["turn"]
    log_success(f"Campaign advanced to turn {turn_num}, world_version={new_version}")
    return turn_num, new_version


async def _verify_replay(api: httpx.AsyncClient, playthrough_id: UUID) -> None:
    log_step("5. Replay & History", "Verifying snapshot at turn 0 and replay steps")
    hist_res = await api.get(f"/v1/playthroughs/{playthrough_id}/history/0")
    assert hist_res.status_code == 200, f"History read failed: {hist_res.text}"
    replay_res = await api.post(
        f"/v1/playthroughs/{playthrough_id}/replay/verify?through_turn=1"
    )
    assert replay_res.status_code == 200, (
        f"Replay verification failed: {replay_res.text}"
    )
    verified_turn = replay_res.json()["verified_turn"]
    log_success(
        f"History snapshot valid! Replay verified up to turn {verified_turn} with 100% hash parity"
    )


async def probe_standard_campaign(api: httpx.AsyncClient) -> None:
    playthrough_id, version = await _init_campaign(api)
    await _check_world_view(api, playthrough_id)
    version = await _submit_tax_command(api, playthrough_id, version)
    _, version = await _advance_turn(api, playthrough_id, version)
    await _verify_replay(api, playthrough_id)


async def _verify_battle_detail(
    api: httpx.AsyncClient, base: str, battle_id: str
) -> None:
    detail_res = await api.get(f"{base}/battles/{battle_id}")
    assert detail_res.status_code == 200
    for field in ("actual_troops", "actual_strength", "accounting", "rng"):
        assert field not in detail_res.text, f"Leaked {field} in battle detail!"
    log_success(
        "Battle detail verified (observer-safe projection, secret data redacted)"
    )


async def _advance_battle_wave(api: httpx.AsyncClient, base: str, version: int) -> int:
    opened = await api.post(
        f"{base}/end-turn",
        json={
            "operation_id": "probe_battle_begin",
            "expected_world_version": version,
            "expected_turn": 0,
            "expected_wave": 0,
        },
    )
    assert opened.status_code == 200 and opened.json()["status"] == "awaiting_commands"
    new_version = opened.json()["world_version"]

    wave_1 = await api.post(
        f"{base}/battles/advance",
        json={
            "operation_id": "probe_wave_1",
            "expected_world_version": new_version,
            "expected_turn": 0,
            "expected_wave": 1,
        },
    )
    assert wave_1.status_code == 200
    res_version = wave_1.json()["world_version"]
    log_success(
        f"Wave 1 completed! Status={wave_1.json()['status']}, world_version={res_version}"
    )
    return res_version


async def _check_wave_report(api: httpx.AsyncClient, base: str, battle_id: str) -> None:
    reports = await api.get(f"{base}/battles/{battle_id}/reports?limit=5")
    assert reports.status_code == 200 and len(reports.json()["items"]) >= 1
    report = reports.json()["items"][0]
    log_success(
        f"Wave exchange report received: battle={report['battle_id']}, "
        f"exchange_index={report['exchange_index']}, total_exchange={report['total_exchange']}"
    )


async def probe_tactical_battle(
    api: httpx.AsyncClient, db_connection: AsyncConnection
) -> None:
    log_step(
        "6. Tactical Battle", "Seeding active battle with attacker and defender armies"
    )
    playthrough_id = await seed_battle(db_connection, orders=6)
    base = f"/v1/playthroughs/{playthrough_id}"
    battles_page = await api.get(f"{base}/battles")
    assert battles_page.status_code == 200
    battle_id = battles_page.json()["items"][0]["id"]
    log_success(f"Battle found: id={battle_id}")

    await _verify_battle_detail(api, base, battle_id)
    log_step(
        "7. Wave Advancement",
        "Stepping through battle wave resolution via /battles/advance",
    )
    await _advance_battle_wave(api, base, 1)
    await _check_wave_report(api, base, battle_id)


async def _trigger_shortfall_pause(
    api: httpx.AsyncClient, base: str
) -> tuple[UUID, int]:
    paused = await api.post(
        f"{base}/end-turn",
        json={
            "operation_id": "probe_shortfall_begin",
            "expected_world_version": 1,
            "expected_turn": 0,
            "expected_wave": 0,
        },
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "awaiting_scene", (
        f"Expected awaiting_scene, got {paused.json()['status']}"
    )
    scene_id = paused.json()["scene_id"]
    version = paused.json()["world_version"]
    log_success(f"Turn safely paused at Economy Phase! scene_id={scene_id}")
    return UUID(scene_id), version


async def _submit_shortfall_choice(
    api: httpx.AsyncClient, base: str, scene_id: UUID, version: int
) -> None:
    log_step(
        "9. Resolve Shortfall Choice",
        "Submitting shortfall_take_loan via /scenes/{id}/choice",
    )
    choice_payload = {
        "operation_id": "probe_choice_loan",
        "expected_world_version": version,
        "expected_turn": 0,
        "expected_wave": 0,
        "choice": "shortfall_take_loan",
    }
    choice_res = await api.post(f"{base}/scenes/{scene_id}/choice", json=choice_payload)
    assert choice_res.status_code == 200, f"Choice failed: {choice_res.text}"
    new_version = choice_res.json()["world_version"]
    status = choice_res.json()["status"]
    log_success(
        f"Choice resolved! Turn completed successfully, status={status}, world_version={new_version}"
    )


async def probe_economy_shortfall(
    api: httpx.AsyncClient, db_connection: AsyncConnection
) -> None:
    log_step(
        "8. Economy Shortfall",
        "Seeding treasury deficit to test turn pause and HTTP choice",
    )
    world, scenario = make_shortfall_world()
    playthrough_id = await seed_world(db_connection, world, scenario)
    base = f"/v1/playthroughs/{playthrough_id}"
    scene_id, version = await _trigger_shortfall_pause(api, base)
    await _submit_shortfall_choice(api, base, scene_id, version)


async def main() -> None:
    print("\n" + "=" * 65)
    print("  STRATEGY SIMULATION SYSTEM: LIVE CAMPAIGN PROBE")
    print("=" * 65 + "\n")

    os.environ["SECRET_KEY"] = SHARED_SECRET
    os.environ["INTERNAL_SERVICE_TOKEN"] = INTERNAL_TOKEN
    os.environ["ENVIRONMENT"] = "testing"
    get_settings.cache_clear()

    app = create_app()

    test_db_url = os.environ.get(
        "SIMULATION_TEST_DATABASE_URL",
        "postgresql://simulation_db:simulation_db@127.0.0.1:5434/simulation_test_db",
    )
    connection = await AsyncConnection.connect(test_db_url)
    await connection.set_autocommit(True)

    async def override_connection() -> AsyncGenerator[AsyncConnection, None]:
        yield connection

    app.dependency_overrides[get_connection] = override_connection

    headers = make_auth_header(OWNER_USER_ID)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers,
        timeout=10.0,
    ) as api:
        try:
            await probe_standard_campaign(api)
            print()
            await probe_tactical_battle(api, connection)
            print()
            await probe_economy_shortfall(api, connection)
            print("\n" + "=" * 65)
            print("  \033[1;32mALL 9 PROBE STAGES PASSED CLEANLY!\033[0m")
            print("=" * 65 + "\n")
        finally:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
