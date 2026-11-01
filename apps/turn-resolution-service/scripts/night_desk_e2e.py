"""End-to-end run of the Night Desk scenario against the isolated e2e stack.

Start the stack first (see docker-compose.e2e.night-desk.yml). The run seeds the
scenario with Core's generator, then plays four full nights through Core and TRS
over HTTP with a scripted narrator: obedient (Visitor), a reader of every late
count (Don't Be Late, two input takeovers), a violator (phone echo, unsafe
entry, the poster; Mr. Orr Is In) and a breakdown (Counted). Every run asserts on
the event stream, the client's view of the playthrough, the stored hidden state
and the recorded prompts. The violator run's event stream is written to the
frontend as a trace fixture. Any failed expectation raises.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/night_desk_e2e.py
"""

import asyncio
import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import asyncpg
import httpx
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

CORE_URL = "http://127.0.0.1:18000"
TRS_URL = "http://127.0.0.1:18001"
APP_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/sands_db"
APP_DSN = "postgresql://postgres:postgres@127.0.0.1:15432/sands_db"
REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_DIR = REPO_ROOT / "apps" / "core-api"
SCRIPT_PATH = Path(__file__).with_name("night_desk_script.json")
TRACE_PATH = (
    REPO_ROOT / "apps/frontend/src/features/play/__fixtures__/night_desk_sse_trace.json"
)
TRACE_RUN = "violator"

PLAYER_NAME = "Alex"
STACK_READY_TIMEOUT_SECONDS = 240
TURN_TIMEOUT_SECONDS = 60
WRONG_ENTRY_TEXT = "3:33 AM"
MAX_TURNS = 40
EXPECTED_TURNS = 21
SANITY_START = 85
PASSIVE_DRAIN = 12
HUM_GAIN = 5
CLEAN_SANITY = SANITY_START - PASSIVE_DRAIN + HUM_GAIN
SOFT_PENALTY = 10
FRAGMENT_SLOTS = 3
COUNT_PROMPT_FIRST = "The printer has finished the count."
COUNT_PROMPT_LATER = "The count is face up in the printer tray."
PHONE_PROMPT = "The desk phone rings."
LAMP_PROMPT = "The lamp in Cabin 14 has gone out."
VOICEMAIL_PROMPT = "The answering machine light is blinking."
DRAWER_PROMPT = "The desk drawer is open a little."
TAKEOVER_LINES = ["Get me out of here, Orr", "I feel too much"]
POSTER_FILE = "truefeel-poster.png"
SECRET_STATE_ROOTS = (
    "seed",
    "count",
    "check",
    "fragments",
    "visit",
    "flags",
    "events",
    "visited",
    "cabin",
    "rule_status",
)
SECRET_CLIENT_STRINGS = ('"false_rule"', '"rule_status"', '"fragments"', '"visited"')
SECRET_LABEL_WORDS = ("R4 true", "R4 false", "R6 true", "R6 false", "Tell:", "seed")
SECRET_PROMPT_KEYS = ("result", "mutations", "timeout_result", "hidden_result")
UNREVEALED_RULE_NUMBERS = (6, 7, 8)
EXPECTED_ENDINGS = {
    "obedient_r6": "Visitor",
    "reader": "Don't Be Late",
    "violator": "Mr. Orr Is In",
    "breakdown": "Counted",
}


@dataclass
class TurnRecord:
    request: dict[str, object]
    events: list[dict[str, object]]


@dataclass
class RunResult:
    name: str
    playthrough_id: uuid.UUID
    turns: list[TurnRecord] = field(default_factory=list)
    ended: dict[str, object] | None = None
    checks: list[dict[str, object]] = field(default_factory=list)
    minigames: list[dict[str, object]] = field(default_factory=list)


def event_names(turn: TurnRecord) -> list[str]:
    return [str(event["event"]) for event in turn.events]


def first_event(turn: TurnRecord, name: str) -> dict[str, object] | None:
    found = next((e for e in turn.events if e["event"] == name), None)
    return found["data"] if found else None  # type: ignore[return-value]


async def wait_for_stack(client: httpx.AsyncClient) -> None:
    deadline = time.monotonic() + STACK_READY_TIMEOUT_SECONDS
    for name, url in (("core", f"{CORE_URL}/health"), ("trs", f"{TRS_URL}/health")):
        while True:
            try:
                if (await client.get(url)).status_code == 200:
                    break
            # NOTE: The stack is still starting; retry until the deadline below.
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError(f"{name} did not become healthy")
            await asyncio.sleep(1.0)


async def create_creator() -> uuid.UUID:
    user_id = uuid.uuid4()
    engine = create_async_engine(APP_DATABASE_URL)
    async with AsyncSession(engine) as session:
        session.add(
            User(
                user_id=user_id,
                display_name="E2E Creator",
                auth_provider_id=f"e2e-{user_id}",
            )
        )
        await session.commit()
    await engine.dispose()
    return user_id


def seed_scenario(creator_id: uuid.UUID) -> uuid.UUID:
    """Runs Core's own generator against the e2e database; it refuses to seed
    anything that fails the Core API's validators."""
    environment = {
        "DATABASE_URL": APP_DATABASE_URL,
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(CORE_DIR),
    }
    command = [
        str(CORE_DIR / ".venv/bin/python"),
        "-W",
        "ignore",
        "-m",
        "scripts.seed_night_desk",
        "--creator-id",
        str(creator_id),
    ]
    completed = subprocess.run(
        command,
        cwd=CORE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"seed failed: {completed.stderr or completed.stdout}")
    return scenario_id_from_database_name()


def scenario_id_from_database_name() -> uuid.UUID:
    return uuid.uuid5(
        uuid.UUID("7d0a2c1e-5b3f-4e8a-9c61-2f4d8b6a1e90"),
        "scenario:night-desk-floor-9",
    )


async def claim_scenario(scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """A re-run against a kept database finds the scenario owned by the previous
    run's creator, because seeding never changes an existing scenario's owner."""
    connection = await asyncpg.connect(APP_DSN)
    try:
        await connection.execute(
            "UPDATE scenarios SET creator_id = $2 WHERE scenario_id = $1",
            scenario_id,
            user_id,
        )
    finally:
        await connection.close()


def auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"x-dev-user-id": str(user_id)}


async def start_playtest(
    client: httpx.AsyncClient, user_id: uuid.UUID, scenario_id: uuid.UUID
) -> dict[str, object]:
    response = await client.post(
        f"{CORE_URL}/v1/scenarios/{scenario_id}/playtest",
        json={"setup_values": {"character_name": PLAYER_NAME}},
        headers=auth(user_id),
    )
    response.raise_for_status()
    return response.json()


async def set_seed(playthrough_id: uuid.UUID, false_rule: str) -> None:
    connection = await asyncpg.connect(APP_DSN)
    try:
        await connection.execute(
            "UPDATE playthroughs SET state = jsonb_set(state, '{seed,false_rule}', "
            "to_jsonb($2::text)) WHERE playthrough_id = $1",
            playthrough_id,
            false_rule,
        )
    finally:
        await connection.close()


async def stored_state(playthrough_id: uuid.UUID) -> dict[str, object]:
    connection = await asyncpg.connect(APP_DSN)
    try:
        raw = await connection.fetchval(
            "SELECT state FROM playthroughs WHERE playthrough_id = $1", playthrough_id
        )
    finally:
        await connection.close()
    return json.loads(raw) if isinstance(raw, str) else raw


async def fragment_evidence(scenario_id: uuid.UUID) -> dict[str, str]:
    connection = await asyncpg.connect(APP_DSN)
    try:
        rows = await connection.fetch(
            "SELECT label, narrator_instruction FROM scenario_conditions "
            "WHERE scenario_id = $1 AND label ~ '^F[0-9]{2} Fragment f[0-9]$'",
            scenario_id,
        )
    finally:
        await connection.close()
    return {row["label"]: row["narrator_instruction"] for row in rows}


async def unrevealed_rule_texts(scenario_id: uuid.UUID) -> list[str]:
    connection = await asyncpg.connect(APP_DSN)
    try:
        rows = await connection.fetch(
            "SELECT text FROM scenario_sheet_rules WHERE scenario_id = $1 "
            "AND number = ANY($2::int[])",
            scenario_id,
            list(UNREVEALED_RULE_NUMBERS),
        )
    finally:
        await connection.close()
    return [row["text"] for row in rows]


def parse_sse(lines: list[str]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    name, data = "", []
    for line in [*lines, ""]:
        if line.startswith("event:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data.append(line.split(":", 1)[1].lstrip(" "))
        elif not line.strip() and name:
            events.append({"event": name, "data": _decode("\n".join(data))})
            name, data = "", []
    return events


def _decode(payload: str) -> object:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


class NightRunner:
    def __init__(
        self,
        client: httpx.AsyncClient,
        user_id: uuid.UUID,
        scenario_id: uuid.UUID,
        name: str,
        spec: dict[str, object],
        default_narration: str,
    ) -> None:
        self.client, self.user_id, self.scenario_id = client, user_id, scenario_id
        self.name, self.spec = name, spec
        self.default_narration = default_narration
        self.strategy: dict[str, object] = dict(spec.get("strategy", {}))  # type: ignore[arg-type]
        self.moves: list[dict[str, object]] = list(spec.get("moves", []))  # type: ignore[arg-type]
        self.visitors_seen = 0
        self.counts_seen = 0
        self.entity_ids: dict[str, str] = {}
        self.pending_check: dict[str, object] | None = None
        self.pending_minigame: dict[str, object] | None = None

    async def play(self) -> RunResult:
        playthrough = await start_playtest(self.client, self.user_id, self.scenario_id)
        playthrough_id = uuid.UUID(str(playthrough["playthrough_id"]))
        await set_seed(playthrough_id, str(self.spec["seed"]))
        snapshot = playthrough["scenario_snapshot"]
        self.entity_ids = {
            e["canonical_name"]: e["entity_id"]
            for e in snapshot["entities"]  # type: ignore[index,union-attr]
        }
        self.participant_id = str(playthrough["participant_id"])
        self.playthrough_id = playthrough_id
        await self.client.post(f"{TRS_URL}/__e2e/reset")
        result = RunResult(self.name, playthrough_id)
        while result.ended is None and len(result.turns) < MAX_TURNS:
            await self.take_turn(result)
        return result

    async def take_turn(self, result: RunResult) -> None:
        state = await stored_state(self.playthrough_id)
        await self.queue_next_narration(int(state["shift_minutes"]))  # type: ignore[arg-type]
        request = self.next_request()
        events = await self.post_turn(request)
        result.turns.append(TurnRecord(request, events))
        self.pending_check = next(
            (e["data"] for e in events if e["event"] == "check"),
            None,  # type: ignore[misc]
        )
        self.pending_minigame = next(
            (e["data"] for e in events if e["event"] == "minigame"),
            None,  # type: ignore[misc]
        )
        if self.pending_check:
            result.checks.append(self.pending_check)
        if self.pending_minigame:
            result.minigames.append(self.pending_minigame)
        ended = next(
            (e["data"] for e in events if e["event"] == "playthrough_ended"), None
        )
        result.ended = ended  # type: ignore[assignment]

    async def queue_next_narration(self, shift: int) -> None:
        is_gated = self.pending_check is not None or self.pending_minigame is not None
        due = bool(self.moves) and shift >= int(self.moves[0]["at_shift"])  # type: ignore[arg-type]
        if is_gated or not due:
            response = {"narration": self.default_narration, "tool_calls": []}
        else:
            move = self.moves.pop(0)
            response = {
                "narration": move["narration"],
                "tool_calls": self.resolve_placeholders(move["tool_calls"]),
            }
        queued = await self.client.post(f"{TRS_URL}/__e2e/queue", json=[response])
        queued.raise_for_status()

    def resolve_placeholders(self, value: object) -> object:
        if isinstance(value, str) and value.startswith("@entity:"):
            return self.entity_ids[value.removeprefix("@entity:")]
        if isinstance(value, list):
            return [self.resolve_placeholders(item) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve_placeholders(item) for key, item in value.items()}
        return value

    def next_request(self) -> dict[str, object]:
        base = {
            "playthrough_id": str(self.playthrough_id),
            "participant_id": self.participant_id,
            "client_action_id": str(uuid.uuid4()),
        }
        if self.pending_check is not None:
            report = {
                "check_id": self.pending_check["check_id"],
                "choice_id": self.choice(self.pending_check),
            }
            if self.pending_check["kind"] == "time_entry" and (
                report["choice_id"] == "enter"
            ):
                report["entry_text"] = self.entry_text(self.pending_check)
            return {
                **base,
                "action_kind": "check_report",
                "action_text": "answer",
                "check_report": report,
            }
        if self.pending_minigame is not None:
            result = {
                "minigame_id": self.pending_minigame["minigame_id"],
                "attempt_id": self.pending_minigame["attempt_id"],
                "outcome_tag": self.minigame_outcome(self.pending_minigame),
            }
            return {
                **base,
                "action_kind": "minigame_result",
                "action_text": "minigame",
                "minigame_result": result,
            }
        return {**base, "action_text": "I wait at the desk.", "action_mode": "do"}

    def choice(self, payload: dict[str, object]) -> str:
        if payload["kind"] == "time_entry":
            self.visitors_seen += 1
            return "reject" if self.visitor_choice() == "reject" else "enter"
        prompt = str(payload["prompt"])
        if prompt in (COUNT_PROMPT_FIRST, COUNT_PROMPT_LATER):
            self.counts_seen += 1
            counts: list[str] = self.strategy.get("counts", ["sign", "leave", "leave"])  # type: ignore[assignment]
            return counts[self.counts_seen - 1]
        answers = {
            PHONE_PROMPT: ("phone", "let_ring"),
            LAMP_PROMPT: ("lamp", "hold"),
            VOICEMAIL_PROMPT: ("voicemail", "play"),
            DRAWER_PROMPT: ("drawer", "open"),
        }
        key, default = answers[prompt]
        return str(self.strategy.get(key, default))

    def visitor_choice(self) -> str:
        choices: list[str] = self.strategy.get("visitor_choices", [])  # type: ignore[assignment]
        return choices[self.visitors_seen - 1] if choices else "told"

    def entry_text(self, payload: dict[str, object]) -> str:
        choice = self.visitor_choice()
        if choice == "told":
            return str(payload["told_label"])
        if choice == "wall":
            return str(payload["wall_label"])
        return WRONG_ENTRY_TEXT

    def minigame_outcome(self, payload: dict[str, object]) -> str:
        assert "Hum" in str(payload["label"]), payload["label"]
        return str(self.strategy.get("hum", "win"))

    async def post_turn(self, request: dict[str, object]) -> list[dict[str, object]]:
        lines: list[str] = []
        async with self.client.stream(
            "POST",
            f"{TRS_URL}/v1/turn",
            json=request,
            headers=auth(self.user_id),
            timeout=TURN_TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                lines.append(line)
        events = parse_sse(lines)
        assert events and events[-1]["event"] == "done", f"{self.name}: {events}"
        return events


def assert_event_order(result: RunResult) -> None:
    for turn in result.turns:
        names = event_names(turn)
        if "sensory_cue" in names:
            assert names.index("sensory_cue") < names.index("narration"), names
        if "check_resolved" in names and "sensory_cue" in names:
            assert names.index("check_resolved") < names.index("sensory_cue"), names
        if "state_update" in names:
            assert names.index("state_update") < names.index("narration"), names
        if "sensory_cue" in names and "state_update" in names:
            assert names.index("sensory_cue") < names.index("state_update"), names
        if "client_effect" in names:
            assert names.index("client_effect") < names.index("done"), names


def assert_no_secrets_in_events(result: RunResult) -> None:
    for check in result.checks:
        leaked = [key for key in SECRET_PROMPT_KEYS if key in json.dumps(check)]
        assert not leaked, f"{result.name}: check payload leaks {leaked}"
    for turn in result.turns:
        summary = first_event(turn, "turn_summary")
        labels = summary.get("active_conditions", []) if summary else []
        named = [name for name in labels if any(w in name for w in SECRET_LABEL_WORDS)]
        assert not named, f"{result.name}: status badges name hidden state: {named}"
        update = first_event(turn, "state_update")
        if update:
            hidden = [root for root in SECRET_STATE_ROOTS if root in update["state"]]  # type: ignore[index,operator]
            assert not hidden, f"{result.name}: state_update leaks {hidden}"


async def assert_client_view_is_clean(
    client: httpx.AsyncClient,
    user_id: uuid.UUID,
    result: RunResult,
    rule_texts: list[str],
) -> None:
    response = await client.get(
        f"{CORE_URL}/v1/playthroughs/{result.playthrough_id}", headers=auth(user_id)
    )
    response.raise_for_status()
    text = json.dumps(response.json())
    assert "false_rule" not in text, f"{result.name}: seed leaked to the client"
    badges = response.json()["active_conditions"]
    assert not [b for b in badges if any(w in b for w in SECRET_LABEL_WORDS)]
    assert not [word for word in SECRET_CLIENT_STRINGS if word in text]
    for rule_text in rule_texts:
        if result.ended is None:
            assert rule_text not in text


async def assert_fragments_respect_the_budget(
    client: httpx.AsyncClient, scenario_id: uuid.UUID, result: RunResult
) -> None:
    evidence = await fragment_evidence(scenario_id)
    prompts = (await client.get(f"{TRS_URL}/__e2e/prompts")).json()
    state = await stored_state(result.playthrough_id)
    slots = [state["fragments"][f"act{act}"] for act in (1, 2, 3)]  # type: ignore[index]
    assert sum(1 for slot in slots if slot) <= FRAGMENT_SLOTS, slots
    for label, text in evidence.items():
        sent = sum(1 for prompt in prompts if text and text in prompt)
        assert sent <= 1, f"{result.name}: {label} was sent {sent} times"


async def assert_run(
    client: httpx.AsyncClient,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    result: RunResult,
    rule_texts: list[str],
) -> dict[str, object]:
    assert result.ended is not None, f"{result.name}: the night never ended"
    assert result.ended["outcome_title"] == EXPECTED_ENDINGS[result.name], result.ended
    assert_event_order(result)
    assert_no_secrets_in_events(result)
    await assert_client_view_is_clean(client, user_id, result, rule_texts)
    await assert_fragments_respect_the_budget(client, scenario_id, result)
    state = await stored_state(result.playthrough_id)
    ASSERTIONS[result.name](result, state)
    return {
        "turns": len(result.turns),
        "ending": result.ended["outcome_title"],
        "sanity": state["sanity"],
        "violations": state["violations_count"],
        "checks": len(result.checks),
        "minigames": [m["label"] for m in result.minigames],
        "effects": [e["kind"] for e in effects_of(result)],
    }


def effects_of(result: RunResult) -> list[dict[str, object]]:
    return [
        event["data"]  # type: ignore[misc]
        for turn in result.turns
        for event in turn.events
        if event["event"] == "client_effect"
    ]


def images_of(result: RunResult) -> list[str]:
    return [
        str(event["data"])
        for turn in result.turns
        for event in turn.events
        if event["event"] == "scene_image"
    ]


def assert_obedient_r6(result: RunResult, state: dict[str, object]) -> None:
    assert len(result.turns) == EXPECTED_TURNS, len(result.turns)
    assert state["sanity"] == CLEAN_SANITY, state["sanity"]
    assert state["violations_count"] == 0
    assert [m["label"] for m in result.minigames] == ["The Hum"]
    assert effects_of(result) == []


def assert_reader(result: RunResult, state: dict[str, object]) -> None:
    assert len(result.turns) == EXPECTED_TURNS, len(result.turns)
    assert state["sanity"] == CLEAN_SANITY - 2 * SOFT_PENALTY, state["sanity"]
    texts = [e["params"]["text"] for e in effects_of(result)]  # type: ignore[index]
    assert texts == TAKEOVER_LINES, texts


def assert_violator(result: RunResult, state: dict[str, object]) -> None:
    kinds = [e["kind"] for e in effects_of(result)]
    assert "phone_echo" in kinds and "input_takeover" in kinds, kinds
    assert state["flags"]["cabin_entered"] is True  # type: ignore[index]
    assert state["rule_status"]["r4"] == "violated"  # type: ignore[index]
    assert state["rule_status"]["r3"] == "violated"  # type: ignore[index]
    assert state["violations_count"] >= 3
    images = images_of(result)
    assert len(images) == 1 and images[0].endswith(POSTER_FILE), images


def assert_breakdown(result: RunResult, state: dict[str, object]) -> None:
    assert int(state["sanity"]) <= 0  # type: ignore[arg-type]
    assert len(result.turns) < EXPECTED_TURNS


ASSERTIONS = {
    "obedient_r6": assert_obedient_r6,
    "reader": assert_reader,
    "violator": assert_violator,
    "breakdown": assert_breakdown,
}


def write_trace(result: RunResult) -> None:
    trace = [{"request": t.request, "events": t.events} for t in result.turns]
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACE_PATH.write_text(json.dumps(trace, separators=(",", ":")), encoding="utf-8")


async def main() -> None:
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    report: dict[str, object] = {}
    async with httpx.AsyncClient(timeout=TURN_TIMEOUT_SECONDS) as client:
        await wait_for_stack(client)
        user_id = await create_creator()
        scenario_id = seed_scenario(user_id)
        await claim_scenario(scenario_id, user_id)
        rule_texts = await unrevealed_rule_texts(scenario_id)
        for name, spec in script["runs"].items():
            runner = NightRunner(
                client, user_id, scenario_id, name, spec, script["narration"]
            )
            result = await runner.play()
            report[name] = await assert_run(
                client, user_id, scenario_id, result, rule_texts
            )
            if name == TRACE_RUN:
                write_trace(result)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
