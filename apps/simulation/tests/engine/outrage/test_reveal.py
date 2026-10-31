from app.engine.outrage.ledger import OUTRAGE_REVEALED, raise_outrage
from app.engine.summaries.projection import project_summary_fact
from app.models.world_events import EventLogEntry
from strategy_contracts.scene import OutrageLevel

from tests.engine.outrage.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)


def _raise(offender_id: str, level: OutrageLevel) -> list[EventLogEntry]:
    world = make_world()
    return raise_outrage(
        world, SCENARIO, faction_id=WRATHFUL_RIVAL, offender_id=offender_id, level=level
    )


def _kinds(events: list[EventLogEntry]) -> list[str]:
    return [event.kind for event in events]


def test_an_enraged_rival_will_name_the_player_as_the_cause() -> None:
    events = _raise(PLAYER, OutrageLevel.ENRAGED)

    reveal = next(event for event in events if event.kind == OUTRAGE_REVEALED)
    assert reveal.is_major
    assert reveal.cause.subject_ids == [PLAYER, WRATHFUL_RIVAL]


def test_a_minor_slight_has_no_reveal() -> None:
    assert OUTRAGE_REVEALED not in _kinds(_raise(PLAYER, OutrageLevel.OFFENDED))


def test_an_npc_quarrel_is_not_revealed_to_the_player() -> None:
    assert OUTRAGE_REVEALED not in _kinds(_raise(CAUTIOUS_RIVAL, OutrageLevel.ENRAGED))


def test_the_summary_fact_names_the_rival_without_any_numbers() -> None:
    world = make_world()
    events = raise_outrage(
        world,
        SCENARIO,
        faction_id=WRATHFUL_RIVAL,
        offender_id=PLAYER,
        level=OutrageLevel.ENRAGED,
    )
    reveal = next(event for event in events if event.kind == OUTRAGE_REVEALED)

    fact = project_summary_fact(world, reveal)

    assert fact is not None
    assert fact.values == {"about_faction_id": WRATHFUL_RIVAL}
    assert fact.text_key == OUTRAGE_REVEALED
