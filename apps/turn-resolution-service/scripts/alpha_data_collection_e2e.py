"""End-to-end run of alpha data collection against the isolated e2e stack.

Start the stack first (see docker-compose.e2e.alpha.yml). A tester plays one
turn and replays it, posts client events, leaves feedback, flags a narration
and answers both surveys; the run then checks the stored rows, the pseudonymous
export and the purge script's dry run. Any failed expectation raises.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/alpha_data_collection_e2e.py
"""

import asyncio
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from alpha_perimeter_e2e import (
    CONSENT_VERSION,
    exchange,
    expect,
    extract_invite_code,
    publish_night_desk,
    run_invite_script,
    sql,
    start_night_desk_run,
)
from night_desk_e2e import (
    APP_DATABASE_URL,
    CORE_DIR,
    CORE_URL,
    TRS_URL,
    create_creator,
    parse_sse,
    seed_scenario,
    wait_for_stack,
)

TESTER_LABEL = "e2e-data-tester"
TURN_TIMEOUT_SECONDS = 60
DISPLAY_NAME_MARKERS = ("display_name", "auth_provider_id")
PURGE_REFUSED_EXIT = 2
LONG_AGO = "2026-10-27"
RETENTION_DAYS = "90"
SESSION_ID = "e2e-session-1"


def run_core_script(module: str, *argv: str) -> subprocess.CompletedProcess[str]:
    environment = {
        "DATABASE_URL": APP_DATABASE_URL,
        "ALPHA_CONSENT_VERSION": CONSENT_VERSION,
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(CORE_DIR),
    }
    return subprocess.run(
        [str(CORE_DIR / ".venv/bin/python"), "-W", "ignore", "-m", module, *argv],
        cwd=CORE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


async def sign_up(client: httpx.AsyncClient) -> dict[str, str]:
    created = run_invite_script("create", "--label", TESTER_LABEL)
    admitted = await exchange(
        client,
        invite_code=extract_invite_code(created),
        alpha_consent_version=CONSENT_VERSION,
    )
    expect(admitted.status_code == 200, "the tester signs up with consent")
    return {"Authorization": f"Bearer {admitted.json()['access_token']}"}


async def play_turn(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    playthrough: dict[str, object],
    action_id: str,
) -> list[str]:
    request = {
        "playthrough_id": playthrough["playthrough_id"],
        "participant_id": playthrough["participant_id"],
        "client_action_id": action_id,
        "action_text": "I look around.",
    }
    async with client.stream(
        "POST",
        f"{TRS_URL}/v1/turn",
        json=request,
        headers=headers,
        timeout=TURN_TIMEOUT_SECONDS,
    ) as response:
        lines = [line async for line in response.aiter_lines()]
    return [str(event["event"]) for event in parse_sse(lines)]


async def check_turn_metrics(playthrough_id: str, action_id: str) -> str:
    rows = await sql(
        "SELECT m.total_ms, m.step_durations, m.replay_count, t.turn_id "
        "FROM turn_metrics m JOIN turn_logs t ON t.turn_id = m.turn_id "
        "WHERE m.playthrough_id = $1",
        uuid.UUID(playthrough_id),
    )
    expect(len(rows) == 1, "one turn produced exactly one turn_metrics row")
    expect(rows[0]["total_ms"] is not None, "the metrics row has a total time")
    expect("request_receiver" in rows[0]["step_durations"], "step timings are stored")
    return str(rows[0]["turn_id"])


async def check_replay(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    playthrough: dict[str, object],
    action_id: str,
) -> None:
    names = await play_turn(client, headers, playthrough, action_id)
    expect(names[-1] == "done", "a replayed action completes")
    rows = await sql(
        "SELECT replay_count FROM turn_metrics WHERE playthrough_id = $1",
        uuid.UUID(str(playthrough["playthrough_id"])),
    )
    expect(
        len(rows) == 1 and rows[0]["replay_count"] == 1, "a replay counts, adds no row"
    )


def events_body(
    playthrough_id: str, events: list[dict[str, object]] | None = None
) -> dict[str, object]:
    default_events = [
        {"name": "session_start", "props": {}},
        {
            "name": "tension_rating",
            "playthrough_id": playthrough_id,
            "props": {"turn_number": 1, "rating": 4},
        },
    ]
    return {"session_id": SESSION_ID, "events": events or default_events}


async def check_events(
    client: httpx.AsyncClient, headers: dict[str, str], playthrough_id: str
) -> None:
    accepted = await client.post(
        f"{CORE_URL}/v1/alpha/events",
        json=events_body(playthrough_id),
        headers=headers,
    )
    expect(accepted.status_code == 202, "client events are accepted")
    unknown = await client.post(
        f"{CORE_URL}/v1/alpha/events",
        json=events_body(playthrough_id, [{"name": "narration_text", "props": {}}]),
        headers=headers,
    )
    expect(unknown.status_code == 422, "an unknown event name is rejected")
    rows = await sql(
        "SELECT name, source FROM alpha_events WHERE session_id = $1 ORDER BY name",
        SESSION_ID,
    )
    expect(
        [row["name"] for row in rows] == ["session_start", "tension_rating"],
        "both events are stored",
    )


async def check_feedback_and_flags(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    playthrough_id: str,
    turn_id: str,
) -> None:
    feedback = await client.post(
        f"{CORE_URL}/v1/alpha/feedback",
        json={
            "playthrough_id": playthrough_id,
            "turn_number": 1,
            "category": "confusing",
            "body": "The phone rule was unclear.",
        },
        headers=headers,
    )
    expect(feedback.status_code == 201, "feedback is stored")
    flag_url = f"{CORE_URL}/v1/alpha/turns/{turn_id}/flag"
    await client.post(flag_url, json={"reasons": ["broke_rule"]}, headers=headers)
    second = await client.post(
        flag_url, json={"reasons": ["too_long"]}, headers=headers
    )
    flags = await sql("SELECT reasons FROM alpha_narration_flags")
    expect(
        second.status_code == 200 and len(flags) == 1,
        "a second flag replaces the first",
    )


async def check_surveys(
    client: httpx.AsyncClient, headers: dict[str, str], playthrough_id: str
) -> None:
    url = f"{CORE_URL}/v1/alpha/survey"
    intake = {
        "kind": "intake",
        "answers": {"horror_experience": "some", "usual_device": "phone"},
    }
    first = await client.post(url, json=intake, headers=headers)
    again = await client.post(url, json=intake, headers=headers)
    expect(
        (first.status_code, again.status_code) == (201, 409), "intake is answered once"
    )
    post_run = {
        "kind": "post_run",
        "playthrough_id": playthrough_id,
        "answers": {"rating": 4, "scariness": 5},
    }
    stored = await client.post(url, json=post_run, headers=headers)
    expect(stored.status_code == 201, "the post-run survey is stored")


def check_export(user_id: str) -> None:
    for kind in ("transcripts", "metrics", "events", "feedback", "surveys"):
        completed = run_core_script("scripts.export_alpha_data", kind)
        expect(completed.returncode == 0, f"export {kind} runs")
        expect(user_id in completed.stdout, f"export {kind} is keyed by user_id")
        leaked = [m for m in DISPLAY_NAME_MARKERS if m in completed.stdout]
        expect(leaked == [], f"export {kind} carries no display name or provider id")


async def check_purge_dry_run() -> None:
    today = datetime.now(UTC).date().isoformat()
    refused = run_core_script("scripts.purge_alpha_data", "--ended-on", today)
    expect(refused.returncode == PURGE_REFUSED_EXIT, "purge refuses before retention")
    dry = run_core_script(
        "scripts.purge_alpha_data",
        "--ended-on",
        LONG_AGO,
        "--retention-days",
        RETENTION_DAYS,
    )
    expect(dry.returncode == 0 and "Dry run" in dry.stdout, "the dry run prints counts")
    rows = await sql("SELECT 1 FROM alpha_events")
    expect(len(rows) > 0, "a dry run deleted nothing")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        await wait_for_stack(client)
        creator_id = await create_creator()
        night_desk_id = seed_scenario(creator_id)
        await publish_night_desk(night_desk_id)
        headers = await sign_up(client)
        started = await start_night_desk_run(client, headers, night_desk_id)
        playthrough = started.json()
        playthrough_id = str(playthrough["playthrough_id"])
        action_id = str(uuid.uuid4())
        names = await play_turn(client, headers, playthrough, action_id)
        expect(names[-1] == "done", "the tester's turn completes")
        turn_id = await check_turn_metrics(playthrough_id, action_id)
        await check_replay(client, headers, playthrough, action_id)
        await check_events(client, headers, playthrough_id)
        await check_feedback_and_flags(client, headers, playthrough_id, turn_id)
        await check_surveys(client, headers, playthrough_id)
        user_id = str(
            (await sql("SELECT user_id FROM alpha_events LIMIT 1"))[0]["user_id"]
        )
        check_export(user_id)
        await check_purge_dry_run()
    sys.stdout.write("\nALPHA DATA COLLECTION E2E PASSED\n")


if __name__ == "__main__":
    asyncio.run(main())
