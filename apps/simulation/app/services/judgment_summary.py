from app.engine.judgments.constants import WITNESS_GOVERNOR_SHIFT
from app.engine.judgments.effects import mercy_value, opinion_value
from strategy_contracts.judgment import (
    JudgmentNuance,
    JudgmentOutcome,
    JudgmentSubjectKind,
    JudgmentVerdict,
)

VERDICT_LABEL = {
    JudgmentVerdict.RELEASE: "Released",
    JudgmentVerdict.EXILE: "Exiled",
    JudgmentVerdict.IMPRISON: "Imprisoned",
    JudgmentVerdict.EXECUTE: "Executed",
}
PUBLIC_ATROCITIES = 2
PRIVATE_ATROCITIES = 1


def _verdict_line(outcome: JudgmentOutcome) -> str:
    label = VERDICT_LABEL[outcome.verdict]
    if outcome.nuance is None:
        return f"Judgment: {label}."
    return f"Judgment: {label} ({outcome.nuance.value.replace('_', ' ')})."


def _atrocity_line(outcome: JudgmentOutcome) -> str:
    if outcome.nuance is JudgmentNuance.QUIETLY:
        return "No atrocity recorded."
    count = (
        PUBLIC_ATROCITIES
        if outcome.nuance is JudgmentNuance.PUBLICLY
        else PRIVATE_ATROCITIES
    )
    return f"Atrocities recorded: {count:+d}."


def _captive_lines(outcome: JudgmentOutcome) -> list[str]:
    regard = opinion_value(outcome)
    cause = "mercy shown" if regard >= 0 else "cruelty shown"
    lines = [f"Regard of the accused's house: {regard:+d} ({cause})."]
    mercy = mercy_value(outcome)
    if mercy != 0:
        lines.append(f"Your reputation for mercy: {mercy:+d}.")
    if outcome.verdict is JudgmentVerdict.EXECUTE:
        lines.append(_atrocity_line(outcome))
    return lines


def _governor_lines(outcome: JudgmentOutcome) -> list[str]:
    keeps_post = outcome.verdict is JudgmentVerdict.RELEASE
    post = (
        "The governor keeps their post."
        if keeps_post
        else "The governor is removed from their post."
    )
    shift = WITNESS_GOVERNOR_SHIFT[outcome.verdict]
    return [
        post,
        f"Your other governors' regard: {shift:+d} (they watched this judgment).",
    ]


def summarize_judgment_outcome(
    outcome: JudgmentOutcome, subject_kind: JudgmentSubjectKind
) -> list[str]:
    """Plain lines naming each consequence of a judgment with its sign and cause."""
    if subject_kind is JudgmentSubjectKind.GOVERNOR:
        return [_verdict_line(outcome), *_governor_lines(outcome)]
    return [_verdict_line(outcome), *_captive_lines(outcome)]
