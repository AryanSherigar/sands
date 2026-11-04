"""The generated Night Desk scenario, played through the real turn pipeline.

Each run plays the pinned fixture with a scripted player and checks the design's
budgets: the length of the night, the sanity total, the fragment cap and spacing,
and the ending. The Core API test next to the generator fails when the fixture is
stale (apps/core-api/tests/scripts/night_desk/test_night_desk_fixture.py).
"""

import pytest
from app.db.models.turn_metrics import TurnMetrics
from night_desk_driver import EXPECTED_TURNS, NightPlayer, Strategy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

SANITY_START = 85
PASSIVE_DRAIN = 12
HUM_GAIN = 5
CLEAN_SANITY = SANITY_START - PASSIVE_DRAIN + HUM_GAIN
SOFT_PENALTY = 10
TAKEOVER_LINES = ["Get me out of here, Orr", "I feel too much"]
ECHO_EFFECT = {"kind": "phone_echo", "params": {"record_ms": 6000, "delay_ms": 2500}}

HIDDEN_ROOTS = (
    "seed",
    "count",
    "check",
    "fragments",
    "visit",
    "flags",
    "events",
    "visited",
    "cabin",
)
SECRET_LABEL_WORDS = ("R4 true", "R4 false", "R6 true", "R6 false", "Tell:", "seed")
SECRET_PROMPT_KEYS = ("result", "mutations", "timeout_result", "hidden_result")


async def _play(session, monkeypatch, strategy):
    return await NightPlayer(session, monkeypatch, strategy).play()


def _names_a_secret(label: str) -> bool:
    return any(word in label for word in SECRET_LABEL_WORDS)


def _assert_events_keep_their_secrets_and_order(result) -> None:
    for names in result.events_by_turn:
        if "sensory_cue" in names and "narration" in names:
            assert names.index("sensory_cue") < names.index("narration")
        if "state_update" in names and "narration" in names:
            assert names.index("state_update") < names.index("narration")
        if "client_effect" in names and "done" in names:
            assert names.index("client_effect") < names.index("done")
    for update in result.state_updates:
        assert not set(HIDDEN_ROOTS) & set(update["state"])
    for check in result.checks:
        assert not set(SECRET_PROMPT_KEYS) & set(check)
    leaked = [label for label in result.badge_labels if _names_a_secret(label)]
    assert leaked == [], "status badges name hidden state"


async def test_the_obedient_night_under_seed_r6(
    db_session: AsyncSession, monkeypatch
) -> None:
    result = await _play(db_session, monkeypatch, Strategy(seed="r6"))

    assert result.turns == EXPECTED_TURNS
    assert result.ended is not None
    assert result.ended["outcome_title"] == "Visitor"
    assert result.sanity == CLEAN_SANITY
    assert result.effects == []
    assert [m["label"] for m in result.minigames] == ["The Hum"]
    _assert_events_keep_their_secrets_and_order(result)


async def test_the_reader_night_sees_both_takeover_lines(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(counts=("sign", "read", "read"))
    result = await _play(db_session, monkeypatch, strategy)

    texts = [
        e["params"]["text"] for e in result.effects if e["kind"] == "input_takeover"
    ]
    assert texts == TAKEOVER_LINES
    assert result.ended is not None
    assert result.ended["outcome_title"] == "Don't Be Late"
    assert result.sanity == CLEAN_SANITY - 2 * SOFT_PENALTY
    prompts = [c["prompt"] for c in result.checks]
    assert prompts.index("The desk phone rings.") > prompts.index(
        "The count is face up in the printer tray."
    )
    _assert_events_keep_their_secrets_and_order(result)


async def test_first_read_at_count_three_gets_line_one(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(counts=("sign", "leave", "read"))
    result = await _play(db_session, monkeypatch, strategy)

    assert [e["params"]["text"] for e in result.effects] == TAKEOVER_LINES[:1]


async def test_picking_up_the_phone_plays_the_echo(
    db_session: AsyncSession, monkeypatch
) -> None:
    result = await _play(db_session, monkeypatch, Strategy(phone="pick_up"))

    assert ECHO_EFFECT in result.effects
    assert result.state["flags"]["line14_lit"] is True


async def test_safe_entry_under_seed_r4_ends_mr_orr_is_in(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(seed="r4", lamp="enter", counts=("sign", "read", "read"))
    result = await _play(db_session, monkeypatch, strategy)

    assert result.ended is not None
    assert result.ended["outcome_title"] == "Mr. Orr Is In"


async def test_unsafe_entry_under_seed_r6_returns_the_clerk_to_the_corridor(
    db_session: AsyncSession, monkeypatch
) -> None:
    result = await _play(db_session, monkeypatch, Strategy(seed="r6", lamp="enter"))

    assert result.state["flags"]["cabin_entered"] is True
    assert result.state["current_location_id"] != result.locations["Cabin 14"]
    assert result.sanity == CLEAN_SANITY - 25


async def test_the_refuser_night_ends_as_visitor(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(
        visitor="reject",
        counts=("leave", "leave", "leave"),
        voicemail="leave",
        drawer="leave",
    )
    result = await _play(db_session, monkeypatch, strategy)

    assert result.turns == EXPECTED_TURNS
    assert result.ended is not None
    assert result.ended["outcome_title"] == "Visitor"


async def test_a_breakdown_ends_as_counted(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(
        seed="r6",
        visitor="wall",
        lamp="enter",
        phone="pick_up",
        counts=("sign", "read", "read"),
        hum="lose",
    )
    result = await _play(db_session, monkeypatch, strategy)

    assert result.ended is not None
    assert result.ended["outcome_title"] == "Counted"
    assert result.turns < EXPECTED_TURNS


async def test_the_poster_is_shown_once_with_its_image(
    db_session: AsyncSession, monkeypatch
) -> None:
    strategy = Strategy(moves=[(20, "Elevator lobby"), (40, "The night desk")])
    result = await _play(db_session, monkeypatch, strategy)

    assert len(result.images) == 1
    assert result.images[0].endswith("truefeel-poster.png")
    assert result.state["fragments"]["poster"] == "shown"


async def test_at_most_one_fragment_per_act(
    db_session: AsyncSession, monkeypatch
) -> None:
    moves = [
        (20, "Records room"),
        (40, "The night desk"),
        (160, "Print room"),
        (180, "Records room"),
        (200, "The night desk"),
    ]
    result = await _play(db_session, monkeypatch, Strategy(moves=moves))

    slots = result.state["fragments"]
    assert all(slots[slot] for slot in ("act1", "act2"))
    assert slots["act3"] in ("", "f5", "f6")
    _assert_events_keep_their_secrets_and_order(result)


async def test_every_turn_of_the_night_has_one_metrics_row(
    db_session: AsyncSession, monkeypatch
) -> None:
    player = NightPlayer(db_session, monkeypatch, Strategy(seed="r6"))

    result = await player.play()

    rows = list(
        (
            await db_session.execute(
                select(TurnMetrics)
                .where(TurnMetrics.playthrough_id == player.playthrough.playthrough_id)
                .order_by(TurnMetrics.turn_number)
            )
        )
        .scalars()
        .all()
    )
    assert [row.turn_number for row in rows] == list(range(1, EXPECTED_TURNS + 1))
    assert all(row.total_ms >= 0 and row.step_durations for row in rows)
    assert any(row.fired_condition_ids for row in rows)
    outcomes = sum(len(row.check_outcomes) for row in rows)
    assert outcomes == len(result.checks) + len(result.minigames)
    assert rows[-1].stat_snapshot["sanity"] == result.sanity
