import pytest
from app.integrations import openai_compatible_client
from app.main import app
from httpx import ASGITransport, AsyncClient

DEV_HEADERS = {"X-Dev-User-Id": "11111111-1111-1111-1111-111111111111"}


@pytest.mark.asyncio
async def test_classify_proclamation_returns_parsed_draft(monkeypatch) -> None:
    fake_response = (
        '{"is_recognized": true, "domain": "martial_levies", "burden": "moderate", '
        '"target_estate": "military", "concession_estate": null, "legal_summary": "Draft 100 archers."}'
    )

    async def fake_chat_completion(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        openai_compatible_client, "chat_completion", fake_chat_completion
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/strategy/proclamation/classify",
            json={"text": "Raise 100 archers from the border."},
            headers=DEV_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_recognized"] is True
        assert data["domain"] == "martial_levies"
        assert data["burden"] == "moderate"


@pytest.mark.asyncio
async def test_classify_proclamation_heuristic_fallback(monkeypatch) -> None:
    async def failing_chat_completion(*args, **kwargs):
        raise RuntimeError("Model unavailable")

    monkeypatch.setattr(
        openai_compatible_client, "chat_completion", failing_chat_completion
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/strategy/proclamation/classify",
            json={"text": "Levy silver from merchant houses."},
            headers=DEV_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_recognized"] is True
        assert data["domain"] == "emergency_taxation"


@pytest.mark.asyncio
async def test_narrate_proclamation_endpoint_streams_dialogue(monkeypatch) -> None:
    async def fake_stream(*args, **kwargs):
        yield "[CHANCELLOR]: The barons will not suffer this quietly."
        yield "[MARSHAL]: Our forces stand ready regardless."

    monkeypatch.setattr(openai_compatible_client, "stream_narration", fake_stream)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/strategy/proclamation/narrate",
            json={
                "draft": {
                    "is_recognized": True,
                    "domain": "martial_levies",
                    "burden": "moderate",
                    "legal_summary": "Raise 200 archers.",
                },
                "turn_context": {"is_war": True},
            },
            headers=DEV_HEADERS,
        )
        assert resp.status_code == 200
        content = resp.text
        assert "event: narration" in content
        assert "CHANCELLOR" in content
        assert "event: done" in content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/strategy/proclamation/classify", {"text": "Levy silver."}),
        (
            "/v1/strategy/proclamation/narrate",
            {
                "draft": {
                    "is_recognized": True,
                    "domain": "martial_levies",
                    "burden": "moderate",
                    "legal_summary": "Raise archers.",
                }
            },
        ),
        (
            "/v1/strategy/playthroughs/11111111-1111-1111-1111-111111111111/events/pe_1/narrate",
            None,
        ),
    ],
)
async def test_unauthenticated_strategy_muse_calls_are_rejected(
    path: str, body: dict[str, object] | None
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(path, json=body)
    assert resp.status_code == 401
