"""Unit tests for PortraitService, with Muse and storage faked."""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from app.exceptions.upload_exceptions import ImageGenerationError
from app.integrations import image_gen_client, storage_client
from app.services.portrait_service import PortraitService
from app.services.rate_limit.policies import QuotaFeature

NO_TEXT_SUFFIX = "No text or lettering in the image."


class _FakeQuota:
    def __init__(self) -> None:
        self.reserved_features: list[QuotaFeature] = []
        self.refund_count = 0

    @asynccontextmanager
    async def reserved(self, feature: QuotaFeature, user: object):
        self.reserved_features.append(feature)
        try:
            yield None
        except BaseException:
            self.refund_count += 1
            raise


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[bytes, str, str]]:
    stored: list[tuple[bytes, str, str]] = []

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        stored.append((content, content_type, object_key))
        return f"https://cdn.example/{object_key}"

    monkeypatch.setattr(storage_client, "upload_image", fake_upload)
    return stored


@pytest.fixture
def prompts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        seen.append(prompt)
        return b"webp-bytes"

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    return seen


async def test_generate_portrait_uploads_under_leader_portraits_prefix(
    prompts: list[str], uploads: list[tuple[bytes, str, str]]
) -> None:
    result = await PortraitService(None).generate_portrait(
        "a stern queen", SimpleNamespace()
    )

    _, content_type, object_key = uploads[0]
    assert object_key.startswith("leader-portraits/")
    assert content_type == image_gen_client.output_content_type()
    assert result.image_url == f"https://cdn.example/{object_key}"


async def test_generate_portrait_appends_no_text_instruction(
    prompts: list[str], uploads: list[tuple[bytes, str, str]]
) -> None:
    await PortraitService(None).generate_portrait("a stern queen", SimpleNamespace())

    assert prompts[0].startswith("a stern queen")
    assert prompts[0].endswith(NO_TEXT_SUFFIX)


async def test_generate_portrait_uses_one_cover_image_quota_unit(
    prompts: list[str], uploads: list[tuple[bytes, str, str]]
) -> None:
    quota = _FakeQuota()

    await PortraitService(quota).generate_portrait("a stern queen", SimpleNamespace())

    assert quota.reserved_features == [QuotaFeature.COVER_IMAGE]


async def test_generate_portrait_muse_failure_propagates_and_refunds(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    async def failing_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        raise ImageGenerationError()

    monkeypatch.setattr(image_gen_client, "generate_image", failing_generate)
    quota = _FakeQuota()

    with pytest.raises(ImageGenerationError):
        await PortraitService(quota).generate_portrait(
            "a stern queen", SimpleNamespace()
        )

    assert quota.refund_count == 1
    assert uploads == []
