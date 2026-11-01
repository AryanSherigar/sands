"""End-to-end run of the alpha perimeter against the isolated e2e stack.

Start the stack first (see docker-compose.e2e.alpha.yml). The run seeds Night
Desk, publishes it, then checks over HTTP that sign-up is gated by invite and
consent, that a tester can only play Night Desk, that locked routes refuse, and
that a turn skips scene images and audio. Any failed expectation raises.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/alpha_perimeter_e2e.py
"""

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import httpx
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent))

from night_desk_e2e import (
    APP_DATABASE_URL,
    APP_DSN,
    CORE_DIR,
    CORE_URL,
    TRS_URL,
    create_creator,
    parse_sse,
    scenario_id_from_database_name,
    seed_scenario,
    wait_for_stack,
)

CONSENT_VERSION = "alpha-1"
DEV_BYPASS_TOKEN = "mock-dev-token"
DEV_BYPASS_UID = "dev-firebase-id-123"
DISABLED_CODE = "alpha_feature_disabled"
INVITE_LABEL = "e2e-tester"
EXTRA_INVITE_LABEL = "e2e-revoked"
LINK_MARKER = "/?invite="
TURN_TIMEOUT_SECONDS = 60
RESULT_LINES: list[str] = []


def record(message: str) -> None:
    RESULT_LINES.append(message)
    sys.stdout.write(f"ok  {message}\n")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    record(message)


async def sql(statement: str, *args: object) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(APP_DSN)
    try:
        return await connection.fetch(statement, *args)
    finally:
        await connection.close()


def run_invite_script(*argv: str) -> str:
    environment = {
        "DATABASE_URL": APP_DATABASE_URL,
        "ALPHA_PUBLIC_URL": "http://127.0.0.1:5173",
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(CORE_DIR),
    }
    completed = subprocess.run(
        [
            str(CORE_DIR / ".venv/bin/python"),
            "-W",
            "ignore",
            "-m",
            "scripts.alpha_invites",
            *argv,
        ],
        cwd=CORE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return completed.stdout


def extract_invite_code(output: str) -> str:
    return output.split(LINK_MARKER)[1].split()[0]


async def exchange(client: httpx.AsyncClient, **fields: str) -> httpx.Response:
    body = {"firebase_id_token": DEV_BYPASS_TOKEN, **fields}
    return await client.post(f"{CORE_URL}/v1/auth/token", json=body)


async def check_signup_gate(client: httpx.AsyncClient) -> str:
    config = (await client.get(f"{CORE_URL}/v1/alpha/config")).json()
    expect(config["is_alpha_mode"] is True, "config reports alpha mode")
    expect(
        config["scenario_id"] == str(scenario_id_from_database_name()),
        "config names Night Desk",
    )
    refused = await exchange(client, alpha_consent_version=CONSENT_VERSION)
    expect(refused.status_code == 403, "no invite is refused")
    expect(refused.json()["code"] == "alpha_invite_required", "no-invite code")
    users = await sql("SELECT 1 FROM users WHERE auth_provider_id = $1", DEV_BYPASS_UID)
    expect(users == [], "a refused sign-up creates no user row")
    bogus = await exchange(
        client, invite_code="bogus", alpha_consent_version=CONSENT_VERSION
    )
    expect(bogus.json()["code"] == "alpha_invite_invalid", "unknown invite is opaque")
    created = run_invite_script("create", "--label", INVITE_LABEL, "--seats", "1")
    code = extract_invite_code(created)
    no_consent = await exchange(client, invite_code=code)
    expect(no_consent.json()["code"] == "alpha_consent_required", "consent is required")
    return code


async def sign_up_tester(client: httpx.AsyncClient, code: str) -> dict[str, str]:
    admitted = await exchange(
        client, invite_code=code, alpha_consent_version=CONSENT_VERSION
    )
    expect(admitted.status_code == 200, "a valid invite creates the account")
    token = admitted.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    again = await exchange(client)
    expect(again.status_code == 200, "an existing account signs in without an invite")
    seats = await sql(
        "SELECT seats_used FROM alpha_invites WHERE label = $1", INVITE_LABEL
    )
    expect(seats[0]["seats_used"] == 1, "the link used exactly one seat")
    profile = (await client.get(f"{CORE_URL}/v1/users/me", headers=headers)).json()
    expect(profile["alpha_consent_is_current"] is True, "consent is on record")
    return headers


async def publish_night_desk(scenario_id: uuid.UUID) -> None:
    await sql(
        "UPDATE scenarios SET status = 'published', published_at = now() "
        "WHERE scenario_id = $1",
        scenario_id,
    )


def build_other_scenario_rows(
    creator_id: uuid.UUID, other_id: uuid.UUID, playthrough_id: uuid.UUID
) -> tuple[Scenario, Playthrough, Participant]:
    scenario = Scenario(
        scenario_id=other_id,
        creator_id=creator_id,
        title="Not the alpha scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
    )
    playthrough = Playthrough(
        playthrough_id=playthrough_id,
        scenario_id=other_id,
        created_by=creator_id,
        scenario_version=1,
        scenario_snapshot={"narrator_persona": "A voice.", "world_data": "x"},
        state={"setup": {}, "narrative": {"opening_prompt": None}},
    )
    participant = Participant(
        playthrough_id=playthrough_id,
        user_id=creator_id,
        role="owner",
        turn_order_position=1,
    )
    return scenario, playthrough, participant


async def add_other_scenario(creator_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    other_id, playthrough_id = uuid.uuid4(), uuid.uuid4()
    rows = build_other_scenario_rows(creator_id, other_id, playthrough_id)
    engine = create_async_engine(APP_DATABASE_URL)
    async with AsyncSession(engine) as session:
        for row in rows:
            session.add(row)
            await session.flush()
        await session.commit()
    await engine.dispose()
    await publish_night_desk(other_id)
    return other_id, playthrough_id


async def start_night_desk_run(
    client: httpx.AsyncClient, headers: dict[str, str], night_desk_id: uuid.UUID
) -> httpx.Response:
    return await client.post(
        f"{CORE_URL}/v1/playthroughs",
        json={
            "scenario_id": str(night_desk_id),
            "setup_values": {"character_name": "Alex"},
        },
        headers=headers,
    )


async def check_scenario_scope(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    night_desk_id: uuid.UUID,
    other_id: uuid.UUID,
) -> dict[str, object]:
    listing = (await client.get(f"{CORE_URL}/v1/scenarios", headers=headers)).json()
    ids = [item["scenario_id"] for item in listing["items"]]
    expect(ids == [str(night_desk_id)], "discovery shows only Night Desk")
    other = await client.get(f"{CORE_URL}/v1/scenarios/{other_id}", headers=headers)
    expect(other.status_code == 404, "another scenario reads as not found")
    refused = await client.post(
        f"{CORE_URL}/v1/playthroughs",
        json={"scenario_id": str(other_id), "setup_values": {}},
        headers=headers,
    )
    expect(
        refused.status_code == 403 and refused.json()["code"] == "alpha_scenario_only",
        "a run of another scenario is refused",
    )
    started = await start_night_desk_run(client, headers, night_desk_id)
    expect(started.status_code == 201, "a Night Desk run starts")
    defaults = await client.get(f"{CORE_URL}/v1/music/defaults")
    expect(defaults.status_code == 200, "music defaults stay open")
    return started.json()


async def check_turn(
    client: httpx.AsyncClient, headers: dict[str, str], playthrough: dict[str, object]
) -> None:
    lines: list[str] = []
    request = {
        "playthrough_id": playthrough["playthrough_id"],
        "participant_id": playthrough["participant_id"],
        "client_action_id": str(uuid.uuid4()),
        "action_text": "I look around.",
        "action_mode": "see",
        "voice_output_requested": True,
    }
    async with client.stream(
        "POST",
        f"{TRS_URL}/v1/turn",
        json=request,
        headers=headers,
        timeout=TURN_TIMEOUT_SECONDS,
    ) as response:
        expect(response.status_code == 200, "a tester turn streams")
        lines = [line async for line in response.aiter_lines()]
    names = [str(event["event"]) for event in parse_sse(lines)]
    expect(names[-1] == "done", "the turn completes")
    banned = {"scene_image", "narration_audio", "quota_notice"}
    expect(banned.isdisjoint(names), "see + voice produce no image, audio or notice")


async def check_locks(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    night_desk_id: uuid.UUID,
    playthrough_id: str,
) -> None:
    locked = [
        ("POST", f"{CORE_URL}/v1/uploads/avatar"),
        ("GET", f"{CORE_URL}/v1/scenarios/{night_desk_id}/music"),
        ("POST", f"{CORE_URL}/v1/scenarios"),
        ("POST", f"{CORE_URL}/v1/scenarios/{night_desk_id}/entities"),
        ("POST", f"{CORE_URL}/v1/playthroughs/{playthrough_id}/share"),
        ("GET", f"{CORE_URL}/v1/creators/me/stats"),
        ("POST", f"{CORE_URL}/v1/playthroughs/join"),
        ("POST", f"{TRS_URL}/v1/voice/transcribe"),
        ("POST", f"{TRS_URL}/v1/studio/assistant"),
        ("GET", f"{TRS_URL}/v1/session/{playthrough_id}/spectate?share_token=x"),
    ]
    for method, url in locked:
        body = {"share_token": "x"} if url.endswith("/join") else {}
        response = await client.request(method, url, headers=headers, json=body)
        is_refused = (
            response.status_code == 403 and response.json().get("code") == DISABLED_CODE
        )
        expect(
            is_refused, f"{method} {url.split('8001')[-1].split('8000')[-1]} is locked"
        )


async def check_old_playthrough(
    client: httpx.AsyncClient, creator_id: uuid.UUID, playthrough_id: uuid.UUID
) -> None:
    participant = (
        await sql(
            "SELECT participant_id FROM participants WHERE playthrough_id = $1",
            playthrough_id,
        )
    )[0]["participant_id"]
    response = await client.post(
        f"{TRS_URL}/v1/turn",
        json={
            "playthrough_id": str(playthrough_id),
            "participant_id": str(participant),
            "client_action_id": str(uuid.uuid4()),
            "action_text": "I look around.",
        },
        headers={"x-dev-user-id": str(creator_id)},
    )
    expect(
        response.status_code == 403
        and response.json()["code"] == "alpha_scenario_only",
        "a turn on an old playthrough is refused",
    )


def check_invite_admin() -> None:
    run_invite_script("create", "--label", EXTRA_INVITE_LABEL)
    run_invite_script("revoke", "--label", EXTRA_INVITE_LABEL)
    listing = run_invite_script("list")
    revoked_line = next(
        line for line in listing.splitlines() if EXTRA_INVITE_LABEL in line
    )
    expect("revoked" in revoked_line, "revoke is visible in the list")
    expect("?invite=" not in listing, "the list never prints codes")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        await wait_for_stack(client)
        creator_id = await create_creator()
        night_desk_id = seed_scenario(creator_id)
        await publish_night_desk(night_desk_id)
        code = await check_signup_gate(client)
        headers = await sign_up_tester(client, code)
        other_id, other_playthrough_id = await add_other_scenario(creator_id)
        playthrough = await check_scenario_scope(
            client, headers, night_desk_id, other_id
        )
        await check_turn(client, headers, playthrough)
        await check_locks(
            client, headers, night_desk_id, str(playthrough["playthrough_id"])
        )
        await check_old_playthrough(client, creator_id, other_playthrough_id)
        check_invite_admin()
    sys.stdout.write(f"\nALPHA PERIMETER E2E PASSED ({len(RESULT_LINES)} checks)\n")


if __name__ == "__main__":
    asyncio.run(main())
