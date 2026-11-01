import pytest
from app.models.battle_progress import IntentRequest
from app.models.intent_briefing import IntentBriefing
from pydantic import ValidationError

from tests.repositories.test_intent_request_repo import request_fixture


def test_intent_briefing_remains_one_shared_model() -> None:
    from app.engine.battles.views import IntentBriefing as EngineBriefing

    assert EngineBriefing is IntentBriefing


def test_intent_request_rejects_mismatched_fallback_scope() -> None:
    request = request_fixture().model_dump(mode="json")
    request["campaign_turn"] = 99
    with pytest.raises(ValidationError, match="identity"):
        IntentRequest.model_validate(request)
