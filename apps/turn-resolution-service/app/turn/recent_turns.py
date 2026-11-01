"""Rendering of the recent-turn window, shared by retrieval and the prompt."""

import uuid

from app.db.models.turn_log import TurnLog
from app.models.turn import RecentTurn

PLAYER_LABEL = "Player"
NARRATOR_LABEL = "Narrator"
SAY_ACTION_MODE = "say"
TURN_SEPARATOR = "\n"


def to_recent_turn(turn_log: TurnLog) -> RecentTurn:
    return RecentTurn(
        turn_number=turn_log.turn_number,
        participant_id=turn_log.participant_id,
        action_mode=turn_log.action_mode,
        action_text=turn_log.action_text,
        narration_text=turn_log.narration_text or "",
    )


def actor_label(participant_id: uuid.UUID | None, names: dict[uuid.UUID, str]) -> str:
    """Single-participant playthroughs keep the plain "Player" label."""
    if len(names) <= 1 or participant_id is None:
        return PLAYER_LABEL
    return names.get(participant_id) or PLAYER_LABEL


def render_turn(turn: RecentTurn, names: dict[uuid.UUID, str]) -> str:
    label = actor_label(turn.participant_id, names)
    return (
        f"{label}: {turn.action_text.strip()}\n"
        f"{NARRATOR_LABEL}: {turn.narration_text.strip()}"
    )


def render_recent_turns(turns: list[RecentTurn], names: dict[uuid.UUID, str]) -> str:
    return TURN_SEPARATOR.join(render_turn(turn, names) for turn in turns)


def fit_recent_text(
    turns: list[RecentTurn], names: dict[uuid.UUID, str], max_chars: int
) -> str:
    """The newest turns that fit `max_chars`, oldest first. A single turn longer
    than the cap is cut to its tail, which holds the most recent prose."""
    chosen: list[str] = []
    used = 0
    for turn in reversed(turns):
        rendered = render_turn(turn, names)
        cost = len(rendered) + len(TURN_SEPARATOR)
        if not chosen and cost > max_chars:
            return rendered[-max_chars:]
        if used + cost > max_chars:
            break
        chosen.append(rendered)
        used += cost
    return TURN_SEPARATOR.join(reversed(chosen))


def last_say_utterance(turns: list[RecentTurn], max_chars: int) -> str:
    for turn in reversed(turns):
        if turn.action_mode == SAY_ACTION_MODE:
            return turn.action_text.strip()[:max_chars]
    return ""
