"""Plays the checked-in Night Desk fixture through the real turn pipeline.

The narrator is a scripted stub: it moves the player with `set_field` when the
clock reaches a scheduled time, and answers every prompt and minigame the way the
strategy says. Nothing here imports the Core API generator; the fixture is a real
pinned snapshot (apps/core-api/tests/scripts/night_desk/test_night_desk_fixture.py).
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.turn.steps import ai_orchestrator
from google.genai import types
from pipeline_seed import seed_master_playthrough, stored_state, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "night_desk_export.json"
MAX_TURNS = 140
EXPECTED_TURNS = 21
WRONG_ENTRY_TEXT = "3:33 AM"


class _Candidate:
    content = "scripted-narrator-turn"


class _Response:
    def __init__(self, calls: list[types.FunctionCall], text: str | None) -> None:
        self.function_calls = calls
        self.text = text
        self.candidates = [_Candidate()]


def scripted_narrator(
    calls: list[types.FunctionCall], text: str, seen_prompts: list[str]
):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        seen_prompts.append(str(system_instruction) + str(contents))
        if calls:
            yield _Response(calls, None)
        yield _Response([], text)

    return _generate


COUNT_PROMPT_FIRST = "The printer has finished the count."
COUNT_PROMPT_LATER = "The count is face up in the printer tray."
PHONE_PROMPT = "The desk phone rings."
LAMP_PROMPT = "The lamp in Cabin 14 has gone out."
VOICEMAIL_PROMPT = "The answering machine light is blinking."
DRAWER_PROMPT = "The desk drawer is open a little."
FRAGMENT_SLOTS = ("act1", "act2", "act3")


@dataclass
class Strategy:
    seed: str = "r6"
    visitor: str = "told"
    counts: tuple[str, str, str] = ("sign", "leave", "leave")
    lamp: str = "hold"
    phone: str = "let_ring"
    voicemail: str = "play"
    drawer: str = "open"
    hum: str = "win"
    moves: list[tuple[int, str]] = field(default_factory=list)
    visitor_for: Callable[[int], str] | None = None


@dataclass
class NightResult:
    turns: int = 0
    ended: dict[str, str] | None = None
    sanity: int = 0
    state: dict[str, object] = field(default_factory=dict)
    fragment_turns: list[int] = field(default_factory=list)
    events_by_turn: list[list[str]] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    checks: list[dict[str, object]] = field(default_factory=list)
    minigames: list[dict[str, object]] = field(default_factory=list)
    state_updates: list[dict[str, object]] = field(default_factory=list)
    badge_labels: set[str] = field(default_factory=set)
    effects: list[dict[str, object]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    locations: dict[str, str] = field(default_factory=dict)


def load_fixture() -> dict[str, dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _location_ids(snapshot: dict[str, object]) -> dict[str, str]:
    return {
        str(entity["canonical_name"]): str(entity["entity_id"])
        for entity in snapshot["entities"]  # type: ignore[union-attr]
        if entity["entity_type"] == "location"
    }


def _event(events, name: str) -> dict[str, object] | None:
    found = next((item for item in events if item.event == name), None)
    return json.loads(found.data) if found else None


def _all_events(events, name: str) -> list[str]:
    return [item.data for item in events if item.event == name]


class NightPlayer:
    def __init__(self, session: AsyncSession, monkeypatch, strategy: Strategy) -> None:
        fixture = load_fixture()
        self.session, self.monkeypatch, self.strategy = session, monkeypatch, strategy
        self.snapshot = fixture["snapshot"]
        self.state = fixture["initial_state"]
        self.state["seed"] = {"false_rule": strategy.seed}
        self.locations = _location_ids(self.snapshot)
        self.pending_check: dict[str, object] | None = None
        self.pending_minigame: dict[str, object] | None = None
        self.visitors_seen = 0
        self.counts_seen = 0
        self.moves = sorted(strategy.moves)
        self.result = NightResult(locations=self.locations)

    async def play(self) -> NightResult:
        self.playthrough, self.participant = await seed_master_playthrough(
            self.session, self.snapshot, self.state
        )
        while self.result.ended is None and self.result.turns < MAX_TURNS:
            await self._take_one_turn()
        stored = await stored_state(self.session, self.playthrough)
        self.result.state = stored
        self.result.sanity = int(stored["sanity"])
        return self.result

    async def _take_one_turn(self) -> None:
        stored = await stored_state(self.session, self.playthrough)
        calls = self._due_moves(int(stored["shift_minutes"]))
        self.monkeypatch.setattr(
            ai_orchestrator.narration_router,
            "stream_with_tools",
            scripted_narrator(calls, "The floor holds still.", self.result.prompts),
        )
        events = await take_turn(
            self.session, self.playthrough, self.participant, **self._request()
        )
        await self._record(events)

    def _due_moves(self, shift: int) -> list[types.FunctionCall]:
        is_due = bool(self.moves) and shift >= self.moves[0][0]
        if not is_due or self._is_gated():
            return []
        _, name = self.moves.pop(0)
        args = {"path": "current_location_id", "value": self.locations[name]}
        return [types.FunctionCall(name="set_field", args=args)]

    def _is_gated(self) -> bool:
        return self.pending_check is not None or self.pending_minigame is not None

    def _request(self) -> dict[str, object]:
        if self.pending_check is not None:
            return self._check_request(self.pending_check)
        if self.pending_minigame is not None:
            outcome = self._minigame_outcome(self.pending_minigame)
            return {
                "action_kind": "minigame_result",
                "action_text": "minigame",
                "minigame_result": {
                    "minigame_id": self.pending_minigame["minigame_id"],
                    "attempt_id": self.pending_minigame["attempt_id"],
                    "outcome_tag": outcome,
                },
            }
        return {"action_text": "I wait at the desk."}

    def _check_request(self, payload: dict[str, object]) -> dict[str, object]:
        report = {"check_id": payload["check_id"], "choice_id": self._choice(payload)}
        if payload["kind"] == "time_entry" and report["choice_id"] == "enter":
            report["entry_text"] = self._entry_text(payload)
        return {
            "action_kind": "check_report",
            "action_text": "answer",
            "check_report": report,
        }

    def _choice(self, payload: dict[str, object]) -> str:
        if payload["kind"] == "time_entry":
            self.visitors_seen += 1
            return "reject" if self._visitor_choice() == "reject" else "enter"
        prompt = str(payload["prompt"])
        if prompt in (COUNT_PROMPT_FIRST, COUNT_PROMPT_LATER):
            self.counts_seen += 1
            return self.strategy.counts[self.counts_seen - 1]
        answers = {
            PHONE_PROMPT: self.strategy.phone,
            LAMP_PROMPT: self.strategy.lamp,
            VOICEMAIL_PROMPT: self.strategy.voicemail,
            DRAWER_PROMPT: self.strategy.drawer,
        }
        return answers[prompt]

    def _visitor_choice(self) -> str:
        if self.strategy.visitor_for is not None:
            return self.strategy.visitor_for(self.visitors_seen)
        return self.strategy.visitor

    def _entry_text(self, payload: dict[str, object]) -> str:
        visitor_choice = self._visitor_choice()
        if visitor_choice == "told":
            return str(payload["told_label"])
        if visitor_choice == "wall":
            return str(payload["wall_label"])
        return WRONG_ENTRY_TEXT

    def _minigame_outcome(self, payload: dict[str, object]) -> str:
        assert "Hum" in str(payload["label"]), payload["label"]
        return self.strategy.hum

    async def _record(self, events) -> None:
        self.result.turns += 1
        self.result.events_by_turn.append([item.event for item in events])
        self.pending_check = _event(events, "check")
        self.pending_minigame = _event(events, "minigame")
        if self.pending_check:
            self.result.checks.append(self.pending_check)
        if self.pending_minigame:
            self.result.minigames.append(self.pending_minigame)
        summary = _event(events, "turn_summary")
        if summary:
            self.result.badge_labels.update(summary.get("active_conditions", []))
        self.result.effects.extend(
            json.loads(data) for data in _all_events(events, "client_effect")
        )
        self.result.images.extend(_all_events(events, "scene_image"))
        update = _event(events, "state_update")
        if update:
            self.result.state_updates.append(update)
        self.result.ended = _event(events, "playthrough_ended")  # type: ignore[assignment]
        stored = await stored_state(self.session, self.playthrough)
        self._track_fragments(stored)

    def _track_fragments(self, stored: dict[str, object]) -> None:
        fragments = stored["fragments"]
        found = sum(1 for slot in FRAGMENT_SLOTS if fragments[slot])  # type: ignore[index]
        found += 1 if fragments["poster"] == "shown" else 0  # type: ignore[index]
        known = len(self.result.fragment_turns)
        self.result.fragment_turns.extend([self.result.turns] * (found - known))


def new_client_action_id() -> uuid.UUID:
    return uuid.uuid4()
