"""Unit tests for MapGenerationService, with Muse and storage faked."""

import threading
from contextlib import asynccontextmanager
from io import BytesIO
from types import SimpleNamespace

import pytest
from app.exceptions.map_generation_exceptions import InvalidRegionImageError
from app.integrations import image_gen_client, storage_client
from app.models.map_generation import MapGenerationRequest
from app.services import map_generation_service
from app.services.map_generation_service import (
    MapGenerationService,
    build_art_prompt,
    build_region_prompt,
    resize_to_match,
    webp_to_png,
)
from app.services.rate_limit.policies import QuotaFeature
from PIL import Image
from pydantic import ValidationError

REGION_SIZE = (1792, 1344)
EDIT_SIZE = (1824, 1376)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _image_bytes(
    size: tuple[int, int], image_format: str, color: tuple[int, int, int]
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=image_format)
    return buffer.getvalue()


class _FakeQuota:
    def __init__(self) -> None:
        self.reserved_features: list[QuotaFeature] = []

    @asynccontextmanager
    async def reserved(self, feature: QuotaFeature, user: object):
        self.reserved_features.append(feature)
        yield None


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[bytes, str, str]]:
    stored: list[tuple[bytes, str, str]] = []

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        stored.append((content, content_type, object_key))
        return f"https://cdn.example/{object_key}"

    monkeypatch.setattr(storage_client, "upload_image", fake_upload)
    return stored


def test_build_region_prompt_asks_for_flat_distinct_regions() -> None:
    prompt = build_region_prompt("a frozen northern realm")

    assert "a frozen northern realm" in prompt
    for phrase in ("about 30", "ONE solid", "distinct", "No text", "no gradients"):
        assert phrase in prompt
    assert "watercolor" not in prompt


def test_build_art_prompt_is_watercolor_without_borders_or_text() -> None:
    prompt = build_art_prompt("a frozen northern realm")

    for phrase in (
        "watercolor",
        "parchment",
        "mist",
        "no lines between regions",
        "No text",
        "Do NOT keep the bright region colors",
    ):
        assert phrase in prompt


def test_request_model_rejects_blank_and_overlong_descriptions() -> None:
    with pytest.raises(ValidationError):
        MapGenerationRequest(description="   ")
    with pytest.raises(ValidationError):
        MapGenerationRequest(description="x" * 501)
    assert MapGenerationRequest(description="  a desert empire  ").description == (
        "a desert empire"
    )


def test_webp_to_png_round_trips_pixels() -> None:
    png = webp_to_png(_image_bytes((4, 4), "WEBP", (255, 0, 0)))

    assert png.startswith(PNG_SIGNATURE)
    decoded = Image.open(BytesIO(png))
    assert decoded.size == (4, 4)
    assert decoded.convert("RGB").getpixel((0, 0))[0] > 240


def test_resize_to_match_returns_exact_target_size() -> None:
    art = _image_bytes(EDIT_SIZE, "WEBP", (200, 190, 160))

    resized = resize_to_match(art, REGION_SIZE)

    decoded = Image.open(BytesIO(resized))
    assert decoded.format == "WEBP"
    assert decoded.size == REGION_SIZE


def test_resize_to_match_same_size_keeps_pixels() -> None:
    art = _image_bytes((64, 48), "WEBP", (10, 20, 30))

    resized = resize_to_match(art, (64, 48))

    assert resized == art


async def test_generate_region_image_calls_muse_and_uploads_png(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    calls: list[tuple[str, str | None]] = []

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        calls.append((prompt, size))
        return _image_bytes(REGION_SIZE, "WEBP", (30, 140, 90))

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    service = MapGenerationService(None)

    result = await service.generate_region_image("a desert empire", SimpleNamespace())

    assert calls == [(build_region_prompt("a desert empire"), "1024x768")]
    content, content_type, object_key = uploads[0]
    assert content.startswith(PNG_SIGNATURE)
    assert content_type == "image/png"
    assert object_key.startswith("scenario-maps/")
    assert object_key.endswith(".png")
    assert (result.width, result.height) == REGION_SIZE
    assert result.region_image_url == f"https://cdn.example/{object_key}"


async def test_generate_region_image_rejects_png_over_five_megabytes(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        return _image_bytes((8, 8), "WEBP", (1, 2, 3))

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(
        map_generation_service,
        "webp_to_png",
        lambda content: PNG_SIGNATURE + b"0" * (5 * 1024 * 1024 + 1),
    )

    with pytest.raises(InvalidRegionImageError):
        await MapGenerationService(None).generate_region_image(
            "x map", SimpleNamespace()
        )

    assert uploads == []


async def test_generate_art_resizes_edit_output_to_region_size(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    async def fake_edit(
        prompt: str, image_bytes: bytes, content_type: str, timeout_seconds: int
    ) -> bytes:
        assert prompt == build_art_prompt("a desert empire")
        assert content_type == "image/png"
        return _image_bytes(EDIT_SIZE, "WEBP", (200, 190, 160))

    monkeypatch.setattr(image_gen_client, "edit_image", fake_edit)
    region_png = _image_bytes(REGION_SIZE, "PNG", (10, 120, 200))

    result = await MapGenerationService(None).generate_art(
        region_png, "a desert empire", SimpleNamespace()
    )

    content, content_type, object_key = uploads[0]
    assert content_type == "image/webp"
    assert object_key.endswith(".webp")
    assert Image.open(BytesIO(content)).size == REGION_SIZE
    assert (result.width, result.height) == REGION_SIZE
    assert result.picture_url == f"https://cdn.example/{object_key}"


@pytest.mark.parametrize("bad_bytes", [b"not a png", PNG_SIGNATURE + b"truncated"])
async def test_generate_art_rejects_invalid_png(
    monkeypatch: pytest.MonkeyPatch, bad_bytes: bytes
) -> None:
    async def fail_edit(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("Muse must not be called")

    monkeypatch.setattr(image_gen_client, "edit_image", fail_edit)

    with pytest.raises(InvalidRegionImageError):
        await MapGenerationService(None).generate_art(
            bad_bytes, "a desert empire", SimpleNamespace()
        )


async def test_each_call_reserves_one_quota_unit(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        return _image_bytes(REGION_SIZE, "WEBP", (30, 140, 90))

    async def fake_edit(*args: object, **kwargs: object) -> bytes:
        return _image_bytes(EDIT_SIZE, "WEBP", (200, 190, 160))

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(image_gen_client, "edit_image", fake_edit)
    quota = _FakeQuota()
    service = MapGenerationService(quota)  # type: ignore[arg-type]

    await service.generate_region_image("a desert empire", SimpleNamespace())
    await service.generate_art(
        _image_bytes(REGION_SIZE, "PNG", (1, 2, 3)),
        "a desert empire",
        SimpleNamespace(),
    )

    assert quota.reserved_features == [QuotaFeature.COVER_IMAGE] * 2


async def test_cpu_bound_image_work_runs_off_the_event_loop(
    monkeypatch: pytest.MonkeyPatch, uploads: list[tuple[bytes, str, str]]
) -> None:
    loop_thread = threading.get_ident()
    worker_threads: list[int] = []

    def recording(original):
        def wrapper(*args):
            worker_threads.append(threading.get_ident())
            return original(*args)

        return wrapper

    for name in ("webp_to_png", "resize_to_match", "_read_png_size"):
        original = getattr(map_generation_service, name)
        monkeypatch.setattr(map_generation_service, name, recording(original))

    async def fake_generate(
        prompt: str, timeout_seconds: int, size: str | None = None
    ) -> bytes:
        return _image_bytes(REGION_SIZE, "WEBP", (30, 140, 90))

    async def fake_edit(*args: object, **kwargs: object) -> bytes:
        return _image_bytes(EDIT_SIZE, "WEBP", (200, 190, 160))

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate)
    monkeypatch.setattr(image_gen_client, "edit_image", fake_edit)
    service = MapGenerationService(None)

    await service.generate_region_image("a desert empire", SimpleNamespace())
    await service.generate_art(
        _image_bytes(REGION_SIZE, "PNG", (1, 2, 3)),
        "a desert empire",
        SimpleNamespace(),
    )

    assert len(worker_threads) >= 4
    assert loop_thread not in worker_threads


async def test_generate_art_rejects_png_with_too_many_pixels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_edit(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("Muse must not be called")

    monkeypatch.setattr(image_gen_client, "edit_image", fail_edit)
    huge_png = _image_bytes((5000, 5000), "PNG", (0, 0, 0))

    with pytest.raises(InvalidRegionImageError):
        await MapGenerationService(None).generate_art(
            huge_png, "a desert empire", SimpleNamespace()
        )
