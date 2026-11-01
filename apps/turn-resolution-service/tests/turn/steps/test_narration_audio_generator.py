"""Unit tests for narration_audio_generator: voice resolution, the 3+-speaker
collapse, and failure handling."""

import json

from app.exceptions.voice_exceptions import NarrationAudioGenerationError
from app.integrations import speech_client, storage_client
from app.turn.speaker_tags import NARRATOR_SPEAKER, SpeakerSpan
from app.turn.steps import narration_audio_generator
from google.genai import errors as genai_errors

_POOL = ("Puck", "Charon", "Fenrir")


async def test_timed_speech_uses_actual_audio_segment_lengths(monkeypatch) -> None:
    uploads = {}

    async def synthesize(spans, voice_map, timeout_seconds):
        samples = 24000 if spans[0].speaker == "narrator" else 12000
        return b"\0\0" * samples, "audio/L16;rate=24000"

    async def upload(content, content_type, object_key):
        uploads[object_key] = (content_type, content)
        return f"https://example.com/{object_key}"

    monkeypatch.setattr(speech_client, "synthesize_narration_audio", synthesize)
    monkeypatch.setattr(storage_client, "upload_image", upload)
    result = await narration_audio_generator.generate_narration_audio(
        "[NARRATOR]\nThe door opens.\n\n[NPC: Asha]\nHello.",
        "Kore",
        _POOL,
        5,
        capture_speaker_timing=True,
    )
    assert result is not None
    metadata = next(
        content for mime, content in uploads.values() if mime == "application/json"
    )
    assert json.loads(metadata)["segments"] == [
        {"speaker": "Asha", "start": 1.0, "end": 1.5}
    ]


def test_find_speaker_voice_map_narrator_only() -> None:
    spans = [SpeakerSpan(NARRATOR_SPEAKER, "You creep through the door.")]

    resolved_spans, voice_map = narration_audio_generator.find_speaker_voice_map(
        spans, "Kore", _POOL
    )

    assert resolved_spans == spans
    assert voice_map == {NARRATOR_SPEAKER: "Kore"}


def test_find_speaker_voice_map_narrator_and_one_npc() -> None:
    spans = [
        SpeakerSpan(NARRATOR_SPEAKER, "You creep through the door."),
        SpeakerSpan("Grimjaw", '"Get out," he growls.'),
    ]

    resolved_spans, voice_map = narration_audio_generator.find_speaker_voice_map(
        spans, "Kore", _POOL
    )

    assert resolved_spans == spans
    assert voice_map[NARRATOR_SPEAKER] == "Kore"
    assert voice_map["Grimjaw"] in _POOL


def test_find_speaker_voice_map_collapses_three_or_more_speakers() -> None:
    spans = [
        SpeakerSpan(NARRATOR_SPEAKER, "The tavern falls silent."),
        SpeakerSpan("Grimjaw", '"Get out," he growls.'),
        SpeakerSpan("Elowen", '"Wait," she says.'),
    ]

    resolved_spans, voice_map = narration_audio_generator.find_speaker_voice_map(
        spans, "Kore", _POOL
    )

    assert resolved_spans == [
        SpeakerSpan(
            NARRATOR_SPEAKER,
            'The tavern falls silent.\n\n"Get out," he growls.\n\n"Wait," she says.',
        )
    ]
    assert voice_map == {NARRATOR_SPEAKER: "Kore"}


async def test_generate_narration_audio_returns_none_for_empty_text(
    monkeypatch,
) -> None:
    result = await narration_audio_generator.generate_narration_audio(
        "", "Kore", _POOL, 5
    )

    assert result is None


async def test_generate_narration_audio_success_uploads_wav(monkeypatch) -> None:
    async def fake_synthesize(spans, voice_map, timeout_seconds):
        return b"\x00\x01" * 100, "audio/L16;rate=24000"

    async def fake_upload_image(
        content: bytes, content_type: str, object_key: str
    ) -> str:
        assert content_type == "audio/wav"
        assert object_key.startswith("narration-audio/")
        assert content[:4] == b"RIFF"
        return f"https://storage.googleapis.com/fake-bucket/{object_key}"

    monkeypatch.setattr(speech_client, "synthesize_narration_audio", fake_synthesize)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload_image)

    result = await narration_audio_generator.generate_narration_audio(
        "[NARRATOR]\nYou creep through the door.", "Kore", _POOL, 5
    )

    assert result is not None
    assert result.audio_url.startswith(
        "https://storage.googleapis.com/fake-bucket/narration-audio/"
    )


async def test_generate_narration_audio_synthesis_failure_returns_none(
    monkeypatch,
) -> None:
    async def fake_synthesize(spans, voice_map, timeout_seconds):
        raise NarrationAudioGenerationError()

    monkeypatch.setattr(speech_client, "synthesize_narration_audio", fake_synthesize)

    result = await narration_audio_generator.generate_narration_audio(
        "[NARRATOR]\nYou creep through the door.", "Kore", _POOL, 5
    )

    assert result is None


async def test_generate_narration_audio_client_error_returns_none(monkeypatch) -> None:
    async def fake_synthesize(spans, voice_map, timeout_seconds):
        raise genai_errors.ClientError(400, {"error": {"message": "blocked"}})

    monkeypatch.setattr(speech_client, "synthesize_narration_audio", fake_synthesize)

    result = await narration_audio_generator.generate_narration_audio(
        "[NARRATOR]\nYou creep through the door.", "Kore", _POOL, 5
    )

    assert result is None


async def test_generate_narration_audio_upload_failure_returns_none(
    monkeypatch,
) -> None:
    from app.exceptions.turn_exceptions import SceneImageGenerationError

    async def fake_synthesize(spans, voice_map, timeout_seconds):
        return b"\x00\x01" * 100, "audio/L16;rate=24000"

    async def fake_upload_image(
        content: bytes, content_type: str, object_key: str
    ) -> str:
        raise SceneImageGenerationError("upload failed")

    monkeypatch.setattr(speech_client, "synthesize_narration_audio", fake_synthesize)
    monkeypatch.setattr(storage_client, "upload_image", fake_upload_image)

    result = await narration_audio_generator.generate_narration_audio(
        "[NARRATOR]\nYou creep through the door.", "Kore", _POOL, 5
    )

    assert result is None
