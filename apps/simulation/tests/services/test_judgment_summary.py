from app.services.judgment_summary import summarize_judgment_outcome
from strategy_contracts.judgment import (
    JudgmentNuance,
    JudgmentOutcome,
    JudgmentSubjectKind,
    JudgmentVerdict,
)


def _lines(verdict, nuance=None, kind=JudgmentSubjectKind.CAPTIVE) -> list[str]:
    return summarize_judgment_outcome(
        JudgmentOutcome(verdict=verdict, nuance=nuance), kind
    )


def test_a_pardon_names_the_verdict_and_signs_every_effect() -> None:
    assert _lines(JudgmentVerdict.RELEASE, JudgmentNuance.WITH_PARDON) == [
        "Judgment: Released (with pardon).",
        "Regard of the accused's house: +12 (mercy shown).",
        "Your reputation for mercy: +15.",
    ]


def test_a_public_execution_records_two_atrocities_and_a_cruel_name() -> None:
    assert _lines(JudgmentVerdict.EXECUTE, JudgmentNuance.PUBLICLY) == [
        "Judgment: Executed (publicly).",
        "Regard of the accused's house: -26 (cruelty shown).",
        "Your reputation for mercy: -20.",
        "Atrocities recorded: +2.",
    ]


def test_a_quiet_execution_records_no_atrocity() -> None:
    assert "No atrocity recorded." in _lines(
        JudgmentVerdict.EXECUTE, JudgmentNuance.QUIETLY
    )


def test_imprisonment_without_a_nuance_has_a_plain_verdict_line() -> None:
    lines = _lines(JudgmentVerdict.IMPRISON)
    assert lines[0] == "Judgment: Imprisoned."
    assert lines[1] == "Regard of the accused's house: -4 (cruelty shown)."


def test_a_governor_judgment_reports_removal_and_the_courts_regard() -> None:
    lines = _lines(
        JudgmentVerdict.EXILE,
        JudgmentNuance.STRIPPED_OF_TITLE,
        JudgmentSubjectKind.GOVERNOR,
    )
    assert lines == [
        "Judgment: Exiled (stripped of title).",
        "The governor is removed from their post.",
        "Your other governors' regard: -2 (they watched this judgment).",
    ]


def test_releasing_a_governor_keeps_them_in_post() -> None:
    lines = _lines(JudgmentVerdict.RELEASE, kind=JudgmentSubjectKind.GOVERNOR)
    assert "The governor keeps their post." in lines
    assert "Your other governors' regard: +3 (they watched this judgment)." in lines
