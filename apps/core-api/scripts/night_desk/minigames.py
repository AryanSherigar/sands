"""Minigames (data doc §9). Each outcome carries its whole consequence as a
mutation list, so no handler conditions or result slots are needed."""

from collections.abc import Sequence

from app.models.minigame import ComposureConfig, ComposureTexts, MinigameCreate
from scripts.night_desk import balance, prose
from scripts.night_desk.expr import (
    DECREMENT,
    INCREMENT,
    SET,
    Expression,
    Mut,
    all_of,
    eq,
    to_state_mutations,
)

HUM_PRIORITY = 0


def _binary(
    label: str,
    minigame_type: str,
    trigger: Expression,
    priority: int,
    outcomes: tuple[Sequence[Mut], Sequence[Mut], Sequence[Mut]],
    template: str,
) -> dict[str, object]:
    win, lose, timeout = (to_state_mutations(items) for items in outcomes)
    return {
        "label": label,
        "minigame_type": minigame_type,
        "trigger_condition_expression": trigger,
        "priority": priority,
        "outcome_mode": "binary",
        "win_mutations": win,
        "lose_mutations": lose,
        "timeout_mutations": timeout,
        "narrator_instruction_template": template,
    }


def _hum_config() -> ComposureConfig:
    return ComposureConfig(
        target_bpm=balance.HUM_BPM,
        beats_to_win=balance.HUM_BEATS,
        tolerance_ms=balance.HUM_TOLERANCE_MS,
        max_strikes=balance.COMPOSURE_MAX_STRIKES,
        audio_profile="hum",
        texts=ComposureTexts(
            instructions=prose.HUM_INSTRUCTIONS,
            win_text=prose.HUM_WIN_TEXT,
            lose_text=prose.HUM_LOSE_TEXT,
        ),
    )


def hum_minigame() -> MinigameCreate:
    won = (
        Mut("sanity", INCREMENT, balance.HUM_GAIN),
        Mut("rule_status.r8", SET, "intact"),
        Mut("flags.hum", SET, "done"),
    )
    lost = (
        Mut("sanity", DECREMENT, balance.HUM_LOSS),
        Mut("rule_status.r8", SET, "violated"),
        Mut("flags.hum", SET, "done"),
    )
    payload = _binary(
        "The Hum",
        "rhythm_composure",
        all_of(eq("events.stairwell", True), eq("flags.hum", "idle")),
        HUM_PRIORITY,
        (won, lost, lost),
        prose.HUM_TEMPLATE,
    )
    return MinigameCreate(**payload, composure_config=_hum_config())  # type: ignore[arg-type]


def minigames() -> list[MinigameCreate]:
    return [hum_minigame()]
