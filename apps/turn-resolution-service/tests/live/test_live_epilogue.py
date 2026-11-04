import re
import warnings
from uuid import uuid4

import pytest
from app.models.token_usage import TokenUsage
from app.services.strategy_epilogue_service import _generate
from strategy_contracts.epilogue import (
    MAX_EPILOGUE_PROSE_CHARS,
    EpilogueBriefing,
    EpilogueClaim,
    EpilogueView,
)
from strategy_contracts.summary import SummaryFact

from .budget_loader import live_budget as live_budget_module

pytestmark = pytest.mark.live_scene

FORBIDDEN_ALWAYS = ("tier", "grade", "score")
DIGITS = re.compile(r"\d")
AUTHOR_HINT = "Remember the harvest festivals and the quiet end of the old rivalry."


def _briefing(**overrides: object) -> EpilogueBriefing:
    fields: dict[str, object] = {
        "playthrough_id": uuid4(),
        "chronicler_id": "teresa",
        "ruler_name": "Aldric",
        "ruler_trait_ids": ["patient", "cautious"],
        "ending_id": "default_graded_end_date",
        "ending_kind": "graded",
        "grade": "triumph",
        "ending_turn": 29,
        "headline_facts": [
            SummaryFact(
                event_id=uuid4(), kind="region_conquered", turn=12, text_key="x"
            )
        ],
        "chronicle_entries": ["Winter came early to the marches."],
    }
    fields.update(overrides)
    return EpilogueBriefing(**fields)


async def _write_closing_entry(briefing: EpilogueBriefing, budget) -> str:
    claim = EpilogueClaim(
        epilogue=EpilogueView(status="pending"), briefing=briefing, input_hash="0" * 64
    )
    usage = TokenUsage()
    chunks: list[str] = []
    async for _ in _generate(claim, chunks, usage):
        pass
    try:
        budget.charge(usage.prompt_tokens, usage.completion_tokens, usage.cached_tokens)
    except live_budget_module.LiveBudgetExhausted:
        pytest.skip("the live token budget is spent")
    return "".join(chunks)


def _assert_a_clean_closing_entry(text: str, briefing: EpilogueBriefing) -> None:
    assert text.strip()
    assert len(text) <= MAX_EPILOGUE_PROSE_CHARS
    lowered = text.lower()
    named = [word for word in FORBIDDEN_ALWAYS if re.search(rf"\b{word}\b", lowered)]
    assert not named, f"named the outcome: {named}"
    assert not DIGITS.search(text), "used a number"
    if briefing.grade and re.search(rf"\b{briefing.grade}\b", lowered):
        warnings.warn(
            f"the closing entry used the word {briefing.grade!r}", stacklevel=2
        )


async def test_a_default_ending_gets_a_clean_closing_entry(live_budget) -> None:
    briefing = _briefing()
    text = await _write_closing_entry(briefing, live_budget)

    _assert_a_clean_closing_entry(text, briefing)


async def test_a_creator_ending_with_a_hint_gets_a_clean_closing_entry(
    live_budget,
) -> None:
    briefing = _briefing(
        ending_id="golden_age",
        ending_kind="victory",
        grade=None,
        ending_name="The Golden Age",
        ending_hint=AUTHOR_HINT,
    )

    text = await _write_closing_entry(briefing, live_budget)

    _assert_a_clean_closing_entry(text, briefing)
