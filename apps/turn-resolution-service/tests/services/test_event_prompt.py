import json
from uuid import uuid4

from app.services.event_prompt import build_event_prompt
from strategy_contracts.events import (
    EventNarrativeBriefing,
    EventNarrativePayload,
)


def make_briefing(
    event_id: str,
    template: str,
    tier: int,
    choices: list[dict[str, str]] | None = None,
) -> EventNarrativeBriefing:
    return EventNarrativeBriefing(
        playthrough_id=uuid4(),
        event_id=event_id,
        template_id=template,
        template_name=template.replace("_", " ").title(),
        subject_name="Dunmere Vale",
        tier=tier,
        cause_description="unrest is 45",
        ruler_name="Aldric Vane",
        ruler_traits=["stern"],
        season_year="Spring 1001",
        choices=choices or [{"choice_id": "c1", "label": "Option 1"}],
    )


def test_two_different_events_share_identical_system_prefix() -> None:
    p1 = build_event_prompt(make_briefing("pe_1", "tax_grievance", 1))
    p2 = build_event_prompt(make_briefing("pe_2", "famine", 3))
    assert p1.system == p2.system
    assert len(p1.system) > 200


def test_event_prompt_schema_dict_matches_payload() -> None:
    prompt = build_event_prompt(make_briefing("pe_1", "tax_grievance", 1))
    assert prompt.schema_dict == EventNarrativePayload.model_json_schema()


def test_event_prompt_user_content_structure_and_sorting() -> None:
    briefing = make_briefing(
        "pe_1",
        "tax_grievance",
        2,
        choices=[
            {"choice_id": "c1", "label": "Grant Relief"},
            {"choice_id": "c2", "label": "Refuse Petition"},
        ],
    )
    prompt = build_event_prompt(briefing)
    parsed = json.loads(prompt.user)
    assert parsed == {
        "cause": "unrest is 45",
        "event": "tax_grievance",
        "offered_choices": ["Grant Relief", "Refuse Petition"],
        "region": "Dunmere Vale",
        "ruler": {"name": "Aldric Vane", "traits": ["stern"]},
        "season_and_year": "Spring 1001",
        "severity_tier": 2,
    }
    assert prompt.user == json.dumps(parsed, sort_keys=True)
