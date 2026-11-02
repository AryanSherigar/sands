from app.models.world_state import WorldState
from strategy_contracts.epilogue import (
    MAX_EPILOGUE_ENTRIES,
    MAX_EPILOGUE_ENTRY_CHARS,
    MAX_EPILOGUE_FACTS,
    EpilogueBriefing,
)
from strategy_contracts.scenario import EndingDefinition
from strategy_contracts.summary import SummaryFact

MAJOR_EVENT_TRIGGER = "major_event"


def _headline_facts(world: WorldState) -> list[SummaryFact]:
    unique: dict[str, SummaryFact] = {}
    for request in world.summary_requests:
        if request.trigger != MAJOR_EVENT_TRIGGER:
            continue
        for fact in request.facts:
            unique[str(fact.event_id)] = fact
    ordered = sorted(unique.values(), key=lambda fact: (fact.turn, str(fact.event_id)))
    return ordered[-MAX_EPILOGUE_FACTS:]


def _latest_entries(entries: list[str]) -> list[str]:
    return [
        entry[:MAX_EPILOGUE_ENTRY_CHARS] for entry in entries[-MAX_EPILOGUE_ENTRIES:]
    ]


def build_epilogue_briefing(
    world: WorldState,
    entries: list[str],
    definition: EndingDefinition | None = None,
) -> EpilogueBriefing:
    ending = world.ending
    if ending is None:
        raise ValueError("an epilogue briefing needs an ended world")
    return EpilogueBriefing(
        playthrough_id=world.playthrough_id,
        chronicler_id=world.ruler.chronicler_id,
        ruler_name=world.ruler.name,
        ruler_trait_ids=list(world.ruler.trait_ids),
        ending_id=ending.ending_id,
        ending_kind=ending.kind.value,
        ending_name=definition.name if definition else "",
        ending_hint=definition.epilogue_hint if definition else "",
        grade=ending.grade.value if ending.grade else None,
        ending_turn=ending.turn,
        headline_facts=_headline_facts(world),
        chronicle_entries=_latest_entries(entries),
    )
