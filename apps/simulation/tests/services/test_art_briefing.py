from uuid import uuid4

from app.models.api_world_view import PendingEventView, UprisingView
from app.services.art_briefing import (
    chronicle_briefing,
    event_briefing,
    uprising_briefing,
)
from strategy_contracts.art import MAX_ART_CAUSES
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.summary import SummaryBriefing, SummaryFact


def _event_view() -> PendingEventView:
    return PendingEventView(
        id="evt-1",
        template_id="tax_grievance",
        name="Tax Grievance",
        subject_kind=ConditionScope.REGION,
        subject_id="carrow",
        subject_name="Carrow Fields",
        region_id="carrow",
        tier=1,
        max_tier=3,
        created_turn=0,
        deadline_turn=3,
        cause_key="tax_grievance",
        choices=[],
    )


def _briefing(fact_count: int) -> SummaryBriefing:
    facts = [
        SummaryFact(
            event_id=uuid4(),
            kind="uprising_started",
            turn=0,
            text_key=f"cause_{index}",
            region_ids=["carrow"],
        )
        for index in range(fact_count)
    ]
    return SummaryBriefing(
        summary_id=uuid4(),
        playthrough_id=uuid4(),
        observer_faction_id="house_carrow",
        requested_turn=0,
        trigger="major_event",
        facts=facts,
    )


def test_event_briefing_uses_template_name_and_subject() -> None:
    briefing = event_briefing(_event_view())
    assert briefing.kind == "event"
    assert briefing.item_id == "evt-1"
    assert briefing.headline == "Tax Grievance"
    assert briefing.subject_name == "Carrow Fields"
    assert briefing.cause_keys == ["tax_grievance"]


def test_uprising_briefing_has_region() -> None:
    view = UprisingView(
        id="upr-1",
        region_id="carrow",
        faction_id="house_carrow",
        started_turn=0,
        trigger_unrest=80,
        income_penalty_percent=10,
        manpower_penalty_percent=10,
        supply_penalty_percent=10,
    )
    briefing = uprising_briefing(view)
    assert briefing.kind == "uprising"
    assert briefing.item_id == "upr-1"
    assert briefing.region_ids == ["carrow"]


def test_chronicle_briefing_caps_causes_at_limit() -> None:
    briefing = chronicle_briefing(_briefing(MAX_ART_CAUSES + 5))
    assert len(briefing.cause_keys) == MAX_ART_CAUSES
    assert briefing.kind == "chronicle"


def test_chronicle_briefing_only_contains_briefing_values() -> None:
    source = _briefing(3)
    allowed = {fact.text_key for fact in source.facts} | {
        region for fact in source.facts for region in fact.region_ids
    }
    briefing = chronicle_briefing(source)
    values = set(briefing.cause_keys) | set(briefing.region_ids)
    assert values <= allowed
    assert briefing.item_id == str(source.summary_id)
