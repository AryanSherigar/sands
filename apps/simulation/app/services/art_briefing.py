from app.models.api_world_view import PendingEventView, UprisingView
from strategy_contracts.art import MAX_ART_CAUSES, ArtBriefing
from strategy_contracts.summary import SummaryBriefing

CHRONICLE_HEADLINE = "A chronicle of recent events"


def event_briefing(view: PendingEventView) -> ArtBriefing:
    return ArtBriefing(
        kind="event",
        item_id=view.id,
        headline=view.name,
        subject_name=view.subject_name,
        region_ids=[view.region_id] if view.region_id else [],
        cause_keys=[view.cause_key],
    )


def uprising_briefing(view: UprisingView) -> ArtBriefing:
    return ArtBriefing(
        kind="uprising",
        item_id=view.id,
        headline=f"{view.stage.value} unrest in the realm",
        region_ids=[view.region_id],
        cause_keys=[view.archetype.value],
    )


def chronicle_briefing(briefing: SummaryBriefing) -> ArtBriefing:
    causes = list(dict.fromkeys(fact.text_key for fact in briefing.facts))
    regions = list(
        dict.fromkeys(region for fact in briefing.facts for region in fact.region_ids)
    )
    return ArtBriefing(
        kind="chronicle",
        item_id=str(briefing.summary_id),
        headline=CHRONICLE_HEADLINE,
        region_ids=regions,
        cause_keys=causes[:MAX_ART_CAUSES],
    )
