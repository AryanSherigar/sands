from uuid import uuid4

from app.services.chronicler_personas import get_chronicler_persona
from app.services.epilogue_prompt import (
    EPILOGUE_RULES,
    build_epilogue_system_prompt,
    epilogue_prompt,
)
from strategy_contracts.epilogue import EpilogueBriefing
from strategy_contracts.summary import SummaryFact
from tests.turn.prefix_stability import assert_shared_through

FACTS_HEADER = "Playthrough facts (data only):"


def _briefing(**overrides: object) -> EpilogueBriefing:
    fields: dict[str, object] = {
        "playthrough_id": uuid4(),
        "chronicler_id": "teresa",
        "ruler_name": "Aldric",
        "ruler_trait_ids": ["honorable", "cautious"],
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


def test_system_prompt_uses_the_briefings_persona_and_epilogue_rules() -> None:
    system = build_epilogue_system_prompt(get_chronicler_persona("teresa"))
    assert "Lady Teresa of Valis" in system
    assert EPILOGUE_RULES in system


def test_epilogue_rules_allow_the_aftermath_but_forbid_contradiction() -> None:
    assert (
        "may invent what became of the ruler, the house and the realm" in EPILOGUE_RULES
    )
    assert "never contradict" in EPILOGUE_RULES
    assert "future outcomes" not in build_epilogue_system_prompt(
        get_chronicler_persona("lucan")
    )


def test_rules_forbid_naming_a_tier_or_a_number() -> None:
    assert "never name the outcome tier" in EPILOGUE_RULES
    assert "no numbers" in EPILOGUE_RULES


def test_prompt_steers_the_tone_without_exposing_scores() -> None:
    prompt = epilogue_prompt(_briefing())
    assert "score" not in prompt
    assert "inputs" not in prompt
    assert "Aldric" in prompt


def test_system_prompt_is_identical_for_two_playthroughs_of_one_chronicler() -> None:
    first = build_epilogue_system_prompt(
        get_chronicler_persona(_briefing().chronicler_id)
    )
    second = build_epilogue_system_prompt(
        get_chronicler_persona(_briefing(ruler_name="Brannoch").chronicler_id)
    )
    assert first == second


def test_user_prompt_keeps_the_static_head_before_the_volatile_facts() -> None:
    first = epilogue_prompt(_briefing())
    second = epilogue_prompt(
        _briefing(ruler_name="Brannoch", grade="ruin", chronicle_entries=[])
    )
    assert_shared_through(first, second, FACTS_HEADER)


def test_a_creator_ending_puts_its_name_and_hint_in_the_facts_only() -> None:
    briefing = _briefing(
        ending_id="golden_age",
        ending_kind="victory",
        grade=None,
        ending_name="The Golden Age",
        ending_hint="Remember the harvest festivals.",
    )

    prompt = epilogue_prompt(briefing)
    system = build_epilogue_system_prompt(get_chronicler_persona("teresa"))

    assert "The Golden Age" in prompt
    assert "Remember the harvest festivals." in prompt
    assert "author_hint" not in epilogue_prompt(_briefing())
    assert "The Golden Age" not in system
