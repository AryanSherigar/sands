from uuid import uuid4

import httpx
import pytest
from app.exceptions.base import BaseAppException
from app.services import strategy_art_service
from strategy_contracts.art import ArtBriefing, ArtClaim, ArtView

ART_URL = "https://cdn.test/strategy-art/one.webp"


def _view(status: str, art_url: str | None = None) -> ArtView:
    return ArtView(kind="event", item_id="evt_1", status=status, art_url=art_url)


def _briefing() -> ArtBriefing:
    return ArtBriefing(kind="event", item_id="evt_1", headline="Tax Grievance")


class _Reservation:
    def __init__(self) -> None:
        self.refund_count = 0

    async def refund(self) -> None:
        self.refund_count += 1


class _Quota:
    def __init__(self) -> None:
        self.reservation = _Reservation()

    async def reserve(self, feature, user_id):
        return self.reservation


class _Client:
    def __init__(self, claim: ArtClaim | Exception) -> None:
        self.claim_result = claim
        self.completed: list[str] = []
        self.failed: list[str] = []

    async def claim(self, identity, kind, item_id, claim_id):
        if isinstance(self.claim_result, Exception):
            raise self.claim_result
        return self.claim_result

    async def complete(self, identity, kind, item_id, request):
        self.completed.append(request.art_url)
        return _view("completed", request.art_url)

    async def fail(self, identity, kind, item_id, request):
        self.failed.append(request.error_code)
        return _view("failed")


def _generating() -> ArtClaim:
    return ArtClaim(art=_view("generating"), briefing=_briefing(), lease_token=uuid4())


async def _run(client: _Client, quota: _Quota) -> ArtView:
    return await strategy_art_service.generate_art(
        uuid4(), "event", "evt_1", uuid4(), client, uuid4(), quota
    )


async def test_completed_claim_returns_saved_url_and_refunds_with_zero_muse_calls(
    monkeypatch,
) -> None:
    calls: list[int] = []

    async def generator(briefing, timeout):
        calls.append(1)
        return ART_URL

    monkeypatch.setattr(strategy_art_service, "generate_strategy_art", generator)
    quota = _Quota()
    saved = ArtClaim(art=_view("completed", ART_URL))
    view = await _run(_Client(saved), quota)
    assert view.art_url == ART_URL
    assert calls == []
    assert quota.reservation.refund_count == 1


async def test_success_claims_generates_completes_and_returns_completed(
    monkeypatch,
) -> None:
    async def generator(briefing, timeout):
        return ART_URL

    monkeypatch.setattr(strategy_art_service, "generate_strategy_art", generator)
    client = _Client(_generating())
    quota = _Quota()
    view = await _run(client, quota)
    assert view.status == "completed"
    assert client.completed == [ART_URL]
    assert quota.reservation.refund_count == 0


async def test_muse_failure_posts_fail_refunds_and_returns_failed_view(
    monkeypatch,
) -> None:
    async def generator(briefing, timeout):
        return None

    monkeypatch.setattr(strategy_art_service, "generate_strategy_art", generator)
    client = _Client(_generating())
    quota = _Quota()
    view = await _run(client, quota)
    assert view.status == "failed"
    assert client.failed == ["provider_unavailable"]
    assert quota.reservation.refund_count == 1


async def test_active_lease_409_refunds_quota_and_propagates() -> None:
    conflict = BaseAppException("art in progress", 409, "art_unavailable")
    quota = _Quota()
    with pytest.raises(BaseAppException):
        await _run(_Client(conflict), quota)
    assert quota.reservation.refund_count == 1


async def test_callback_transport_failure_refunds_and_returns_failed(
    monkeypatch,
) -> None:
    async def generator(briefing, timeout):
        return ART_URL

    class Broken(_Client):
        async def complete(self, identity, kind, item_id, request):
            raise httpx.ConnectError("down")

    monkeypatch.setattr(strategy_art_service, "generate_strategy_art", generator)
    monkeypatch.setattr(strategy_art_service, "COMPLETE_RETRY_DELAY_SECONDS", 0)
    quota = _Quota()
    view = await _run(Broken(_generating()), quota)
    assert view.status == "failed"
    assert quota.reservation.refund_count == 1
