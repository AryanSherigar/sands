from uuid import uuid4

import pytest
from pydantic import ValidationError
from strategy_contracts.art import (
    ART_PROMPT_VERSION,
    MAX_ART_CAUSES,
    ArtBriefing,
    ArtClaim,
    ArtCompleteInput,
    ArtView,
)

MAX_HEADLINE_CHARS = 160


def _briefing(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "event",
        "item_id": "evt-1",
        "headline": "Grain riots",
        "subject_name": "Greenford",
        "region_ids": ["greenford"],
        "cause_keys": ["low_food"],
    }
    return {**base, **overrides}


def test_art_briefing_rejects_overlong_headline() -> None:
    with pytest.raises(ValidationError):
        ArtBriefing(**_briefing(headline="x" * (MAX_HEADLINE_CHARS + 1)))


def test_art_briefing_rejects_too_many_causes() -> None:
    causes = [f"cause_{index}" for index in range(MAX_ART_CAUSES + 1)]
    with pytest.raises(ValidationError):
        ArtBriefing(**_briefing(cause_keys=causes))


def test_complete_input_rejects_unknown_prompt_version() -> None:
    with pytest.raises(ValidationError):
        ArtCompleteInput(
            lease_token=uuid4(), art_url="https://cdn/x.webp", prompt_version="v0"
        )


def test_complete_input_defaults_to_current_prompt_version() -> None:
    request = ArtCompleteInput(lease_token=uuid4(), art_url="https://cdn/x.webp")
    assert request.prompt_version == ART_PROMPT_VERSION


def test_art_view_round_trips_json() -> None:
    view = ArtView(
        kind="chronicle",
        item_id=str(uuid4()),
        status="completed",
        art_url="https://cdn/x.webp",
    )
    assert ArtView.model_validate(view.model_dump(mode="json")) == view


def test_claim_allows_missing_briefing_for_completed_art() -> None:
    view = ArtView(kind="event", item_id="e", status="completed", art_url="https://x/y")
    assert ArtClaim(art=view).briefing is None
