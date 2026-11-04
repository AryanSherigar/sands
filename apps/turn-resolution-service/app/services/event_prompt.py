import json

from pydantic import BaseModel
from strategy_contracts.events import EventNarrativeBriefing, EventNarrativePayload

SYSTEM_PROMPT = (
    "You are the royal chronicler and narrator of a medieval realm facing crises and unrest. "
    "Your duty is to describe an unexpected event or petition brought before the sovereign. "
    "Maintain a grounded, serious historical manuscript tone without modern idioms, flowery melodrama, or anachronisms. "
    "You must output valid JSON matching the schema strictly: "
    "body_prose (1-2 rich paragraphs describing the situation and atmosphere), "
    "cause_quote (a sharp in-character statement from petitioners or heralds), "
    "character_name (the person addressing the throne), "
    "character_title (their office, trade, or role), "
    "and disposition (e.g. Uneasy, Resentful, Defiant, Hopeful)."
)


class EventPrompt(BaseModel):
    system: str
    user: str
    schema_dict: dict[str, object]


def build_event_prompt(briefing: EventNarrativeBriefing) -> EventPrompt:
    user_payload = {
        "event": briefing.template_id,
        "severity_tier": briefing.tier,
        "region": briefing.subject_name,
        "cause": briefing.cause_description,
        "ruler": {
            "name": briefing.ruler_name,
            "traits": briefing.ruler_traits,
        },
        "season_and_year": briefing.season_year,
        "offered_choices": [c["label"] for c in briefing.choices if "label" in c],
    }
    return EventPrompt(
        system=SYSTEM_PROMPT,
        user=json.dumps(user_payload, sort_keys=True),
        schema_dict=EventNarrativePayload.model_json_schema(),
    )
