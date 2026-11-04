from uuid import UUID, uuid4

import pytest
from app.exceptions.base import BaseAppException
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.routers import strategy_events
from app.services import strategy_event_service
from app.services.rate_limit.quota_service import get_quota_service
from app.services.strategy_event_service import narrate_strategy_event
from fastapi import FastAPI
from fastapi.testclient import TestClient
from strategy_contracts.events import (
    EventNarrativeBriefing,
    EventNarrativeClaim,
    EventNarrativeCompleteInput,
    EventNarrativeFailInput,
    EventNarrativePayload,
    EventNarrativeView,
)


class _NoQuota:
    async def reserve(self, feature: object, user_id: UUID) -> None:
        return None


def _sample_payload() -> EventNarrativePayload:
    return EventNarrativePayload(
        body_prose="The peasants gather outside the hall demanding bread.",
        cause_quote="Our granaries are bare, lord!",
        character_name="Eldred",
        character_title="Village Elder",
        disposition="Resentful",
    )


def _sample_briefing(playthrough_id: UUID, event_id: str) -> EventNarrativeBriefing:
    return EventNarrativeBriefing(
        playthrough_id=playthrough_id,
        event_id=event_id,
        template_id="tax_grievance",
        template_name="Tax grievance",
        subject_name="Dunmere Vale",
        tier=1,
        cause_description="unrest is 45",
        ruler_name="Aldric Vane",
        ruler_traits=["stern"],
        season_year="Spring 1001",
        choices=[{"choice_id": "c1", "label": "Lower taxes"}],
    )


class _MockSimulationClient:
    def __init__(
        self,
        view: EventNarrativeView,
        claim: EventNarrativeClaim | BaseAppException | None = None,
    ) -> None:
        self.view = view
        self.claim_result = claim
        self.completed_requests: list[EventNarrativeCompleteInput] = []
        self.failed_requests: list[EventNarrativeFailInput] = []

    async def get(self, identity: UUID, event_id: str) -> EventNarrativeView:
        return self.view

    async def claim(
        self, identity: UUID, event_id: str, claim_id: UUID
    ) -> EventNarrativeClaim | None:
        if isinstance(self.claim_result, Exception):
            raise self.claim_result
        return self.claim_result

    async def complete(
        self, identity: UUID, event_id: str, request: EventNarrativeCompleteInput
    ) -> None:
        self.completed_requests.append(request)

    async def fail(
        self, identity: UUID, event_id: str, request: EventNarrativeFailInput
    ) -> None:
        self.failed_requests.append(request)


async def test_returns_cached_narrative_without_calling_muse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    cached_payload = _sample_payload()
    view = EventNarrativeView(
        event_id="pe_1", status="completed", narration=cached_payload
    )
    client = _MockSimulationClient(view=view)

    async def fail_muse(*args: object, **kwargs: object) -> str:
        raise AssertionError("Muse should not be called for completed narratives")

    monkeypatch.setattr(strategy_event_service, "chat_completion", fail_muse)

    result = await narrate_strategy_event(pid, "pe_1", client, uuid4(), _NoQuota())  # type: ignore[arg-type]
    assert result == cached_payload
    assert not client.completed_requests
    assert not client.failed_requests


async def test_claims_prompts_muse_and_completes_on_new_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    token = uuid4()
    view = EventNarrativeView(event_id="pe_1", status="pending", narration=None)
    claim = EventNarrativeClaim(
        lease_token=token, briefing=_sample_briefing(pid, "pe_1")
    )
    client = _MockSimulationClient(view=view, claim=claim)
    expected_payload = _sample_payload()

    async def fake_muse(*args: object, **kwargs: object) -> str:
        return expected_payload.model_dump_json()

    monkeypatch.setattr(strategy_event_service, "chat_completion", fake_muse)

    result = await narrate_strategy_event(pid, "pe_1", client, uuid4(), _NoQuota())  # type: ignore[arg-type]
    assert result == expected_payload
    assert len(client.completed_requests) == 1
    assert client.completed_requests[0].lease_token == token
    assert client.completed_requests[0].narration == expected_payload
    assert not client.failed_requests


async def test_handles_generation_failure_by_calling_fail_and_returning_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    token = uuid4()
    view = EventNarrativeView(event_id="pe_1", status="pending", narration=None)
    claim = EventNarrativeClaim(
        lease_token=token, briefing=_sample_briefing(pid, "pe_1")
    )
    client = _MockSimulationClient(view=view, claim=claim)

    async def failing_muse(*args: object, **kwargs: object) -> str:
        raise RuntimeError("LLM rate limit or connection error")

    monkeypatch.setattr(strategy_event_service, "chat_completion", failing_muse)

    result = await narrate_strategy_event(pid, "pe_1", client, uuid4(), _NoQuota())  # type: ignore[arg-type]
    assert result is None
    assert not client.completed_requests
    assert len(client.failed_requests) == 1
    assert client.failed_requests[0].lease_token == token
    assert client.failed_requests[0].error_code == "generation_error"


async def test_returns_none_when_claim_is_409_conflict() -> None:
    pid = uuid4()
    view = EventNarrativeView(event_id="pe_1", status="generating", narration=None)
    conflict_exc = BaseAppException("Delivery not claimable", 409, "conflict")
    client = _MockSimulationClient(view=view, claim=conflict_exc)

    result = await narrate_strategy_event(pid, "pe_1", client, uuid4(), _NoQuota())  # type: ignore[arg-type]
    assert result is None
    assert not client.completed_requests
    assert not client.failed_requests


def test_narrate_router_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    pid = uuid4()
    expected = _sample_payload()

    async def fake_narrate(
        playthrough_id: UUID,
        event_id: str,
        client: object,
        user_id: UUID,
        quota: object,
    ) -> EventNarrativePayload:
        return expected

    monkeypatch.setattr(
        "app.routers.strategy_events.narrate_strategy_event", fake_narrate
    )

    test_app = FastAPI()
    test_app.include_router(strategy_events.router)
    test_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid4(), token_version=1
    )
    test_app.dependency_overrides[get_quota_service] = lambda: _NoQuota()
    test_client = TestClient(test_app)
    response = test_client.post(
        f"/v1/strategy/playthroughs/{pid}/events/pe_1/narrate",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
