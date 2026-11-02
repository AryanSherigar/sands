from uuid import uuid4

from app.models.world_events import EndingState, SummaryRequest
from app.services.epilogue_briefing import build_epilogue_briefing
from strategy_contracts.conditions import (
    Comparison,
    ConditionMetric,
    ConditionOperator,
)
from strategy_contracts.endings import EndingGrade
from strategy_contracts.epilogue import (
    MAX_EPILOGUE_ENTRIES,
    MAX_EPILOGUE_ENTRY_CHARS,
    MAX_EPILOGUE_FACTS,
)
from strategy_contracts.scenario import EndingDefinition, EndingKind
from strategy_contracts.summary import SummaryFact
from tests.models.builders import make_world


def _fact(turn: int, kind: str = "battle_won") -> SummaryFact:
    return SummaryFact(event_id=uuid4(), kind=kind, turn=turn, text_key=kind)


def _ended_world(**ending: object):
    world = make_world()
    world.ending = EndingState(
        ending_id="default_graded_end_date",
        kind=EndingKind.GRADED,
        turn=29,
        grade=EndingGrade.TRIUMPH,
        inputs={"score": 91, "strain": 12},
        **ending,
    )
    return world


def test_briefing_names_the_tier_but_carries_no_scores() -> None:
    briefing = build_epilogue_briefing(_ended_world(), [])
    document = briefing.model_dump_json()
    assert briefing.grade == "triumph"
    assert briefing.ending_id == "default_graded_end_date"
    assert briefing.ending_turn == 29
    assert "score" not in document
    assert "strain" not in document


def test_briefing_takes_the_rulers_chronicler_and_identity() -> None:
    world = _ended_world()
    world.ruler = world.ruler.model_copy(update={"chronicler_id": "vaelen"})
    briefing = build_epilogue_briefing(world, [])
    assert briefing.chronicler_id == "vaelen"
    assert briefing.ruler_name == world.ruler.name
    assert briefing.ruler_trait_ids == list(world.ruler.trait_ids)


def test_headline_facts_are_major_events_in_turn_order_and_capped() -> None:
    world = _ended_world()
    facts = [_fact(turn) for turn in range(MAX_EPILOGUE_FACTS + 10)]
    world.summary_requests = [
        SummaryRequest(
            id="major-1", requested_turn=1, trigger="major_event", facts=facts[::-1]
        ),
        SummaryRequest(
            id="sig-1",
            requested_turn=2,
            trigger="significance",
            facts=[_fact(99, "minor_thing")],
        ),
    ]
    briefing = build_epilogue_briefing(world, [])
    turns = [fact.turn for fact in briefing.headline_facts]
    assert len(turns) == MAX_EPILOGUE_FACTS
    assert turns == sorted(turns)
    assert turns[-1] == MAX_EPILOGUE_FACTS + 9
    assert all(fact.kind != "minor_thing" for fact in briefing.headline_facts)


def test_chronicle_entries_keep_the_latest_and_are_truncated() -> None:
    entries = [f"entry {index}" for index in range(MAX_EPILOGUE_ENTRIES + 3)]
    entries[-1] = "x" * (MAX_EPILOGUE_ENTRY_CHARS + 500)
    briefing = build_epilogue_briefing(_ended_world(), entries)
    assert len(briefing.chronicle_entries) == MAX_EPILOGUE_ENTRIES
    assert briefing.chronicle_entries[0] == "entry 3"
    assert len(briefing.chronicle_entries[-1]) == MAX_EPILOGUE_ENTRY_CHARS


def test_a_world_with_no_chronicles_still_builds_a_briefing() -> None:
    briefing = build_epilogue_briefing(_ended_world(), [])
    assert briefing.chronicle_entries == []
    assert briefing.headline_facts == []


def test_a_creator_ending_passes_its_name_and_hint_to_the_chronicler() -> None:
    definition = EndingDefinition(
        id="golden_age",
        kind=EndingKind.VICTORY,
        name="The Golden Age",
        condition=Comparison(
            metric=ConditionMetric.TREASURY,
            operator=ConditionOperator.GTE,
            value=1,
        ),
        epilogue_hint="Remember the harvest festivals.",
    )

    briefing = build_epilogue_briefing(_ended_world(), [], definition)

    assert briefing.ending_name == "The Golden Age"
    assert briefing.ending_hint == "Remember the harvest festivals."
    assert build_epilogue_briefing(_ended_world(), []).ending_hint == ""
