from uuid import uuid4

from app.models.world_events import SummaryRequest
from app.services.summary_materialization import build_summary_briefing
from strategy_contracts.summary import SummaryFact
from tests.models.builders import make_world


def _request() -> SummaryRequest:
    return SummaryRequest(
        id="summary-1",
        requested_turn=2,
        trigger="major_event",
        facts=[
            SummaryFact(
                event_id=uuid4(),
                kind="uprising_started",
                turn=2,
                text_key="uprising_started",
            )
        ],
    )


def test_briefing_carries_the_worlds_chronicler() -> None:
    world = make_world()
    world.ruler = world.ruler.model_copy(update={"chronicler_id": "teresa"})
    briefing = build_summary_briefing(world, _request())
    assert briefing.chronicler_id == "teresa"


def test_briefing_for_a_default_ruler_names_lucan() -> None:
    briefing = build_summary_briefing(make_world(), _request())
    assert briefing.chronicler_id == "lucan"
