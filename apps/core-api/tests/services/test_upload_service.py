"""Unit tests for UploadService's AI cover image generation and audio validation."""

import pytest
from app.exceptions.upload_exceptions import UploadValidationError
from app.integrations import image_gen_client, storage_client
from app.models.image_generation import CoverImageGenerationRequest
from app.services.upload_service import UploadService


def test_build_cover_prompt_includes_title_genre_and_opening_scene() -> None:
    service = UploadService()
    request = CoverImageGenerationRequest(
        title="The Sunken Keep",
        genre_tags=["fantasy", "horror"],
        opening_scene="A storm batters the abandoned watchtower.",
    )

    prompt = service._build_cover_prompt(request)

    assert "The Sunken Keep" in prompt
    assert "fantasy, horror" in prompt
    assert "A storm batters the abandoned watchtower." in prompt


def test_build_cover_prompt_omits_missing_optional_fields() -> None:
    service = UploadService()
    request = CoverImageGenerationRequest(title="Bare Title", genre_tags=[])

    prompt = service._build_cover_prompt(request)

    assert "Bare Title" in prompt
    assert "Genre:" not in prompt
    assert "Opening scene:" not in prompt


async def test_generate_and_upload_cover_image_uses_scenario_covers_prefix(
    monkeypatch,
) -> None:
    async def fake_generate_image(prompt: str, timeout_seconds: int) -> bytes:
        return b"RIFF\x00\x00\x00\x00WEBPfake-image-bytes"

    captured_object_keys: list[str] = []

    async def fake_upload_image(
        content: bytes, content_type: str, object_key: str
    ) -> str:
        captured_object_keys.append(object_key)
        return f"https://storage.googleapis.com/fake-bucket/{object_key}"

    monkeypatch.setattr(image_gen_client, "generate_image", fake_generate_image)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload_image)

    service = UploadService()
    request = CoverImageGenerationRequest(title="A Title", genre_tags=[])
    url = await service.generate_and_upload_cover_image(request, user=None)

    assert url.startswith("https://storage.googleapis.com/fake-bucket/scenario-covers/")
    assert captured_object_keys[0].startswith("scenario-covers/")


async def test_upload_scenario_audio_accepts_valid_mp3_signature(monkeypatch) -> None:
    async def fake_upload_image(
        content: bytes, content_type: str, object_key: str
    ) -> str:
        return f"https://storage.googleapis.com/fake-bucket/{object_key}"

    monkeypatch.setattr(storage_client, "upload_image", fake_upload_image)

    service = UploadService()
    url = await service.upload_scenario_audio(b"\xff\xfb" + b"0" * 100, "audio/mpeg")

    assert url.startswith("https://storage.googleapis.com/fake-bucket/scenario-audio/")


async def test_upload_scenario_audio_rejects_mismatched_mp3_signature() -> None:
    service = UploadService()

    with pytest.raises(UploadValidationError):
        await service.upload_scenario_audio(b"not an mp3 at all", "audio/mpeg")


async def test_upload_scenario_audio_rejects_mismatched_ogg_signature() -> None:
    service = UploadService()

    with pytest.raises(UploadValidationError):
        await service.upload_scenario_audio(b"not an ogg at all", "audio/ogg")


async def test_upload_scenario_audio_wav_signature_check_skipped(monkeypatch) -> None:
    """WAV isn't in the magic-bytes dict; the audio-signature guard must not
    reject a valid WAV file just because it has no registered signature."""

    async def fake_upload_image(
        content: bytes, content_type: str, object_key: str
    ) -> str:
        return f"https://storage.googleapis.com/fake-bucket/{object_key}"

    monkeypatch.setattr(storage_client, "upload_image", fake_upload_image)

    import wave
    from io import BytesIO

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(b"\x00\x00" * 8000)

    service = UploadService()
    url = await service.upload_scenario_audio(buffer.getvalue(), "audio/wav")

    assert url.startswith("https://storage.googleapis.com/fake-bucket/scenario-audio/")
