"""Unit tests for voice_service.py, with speech_client mocked."""

from app.config import settings
from app.exceptions.voice_exceptions import AudioValidationError
from app.integrations import speech_client
from app.services.voice_service import build_phrase_hints, transcribe_turn_action_audio


async def test_transcribe_turn_action_audio_returns_transcript(monkeypatch) -> None:
    async def fake_transcribe_audio(
        content, content_type, timeout_seconds, phrase_hints=None
    ):
        return "I open the door"

    monkeypatch.setattr(speech_client, "transcribe_audio", fake_transcribe_audio)

    result = await transcribe_turn_action_audio(b"fake-audio", "audio/webm")

    assert result.transcript == "I open the door"


async def test_transcribe_turn_action_audio_empty_bytes_raises_validation_error() -> (
    None
):
    try:
        await transcribe_turn_action_audio(b"", "audio/webm")
        raise AssertionError("expected AudioValidationError")
    except AudioValidationError:
        pass


def test_build_phrase_hints_dedupes_names_and_aliases_and_skips_junk() -> None:
    snapshot = {
        "entities": [
            {"canonical_name": "Zhaerith", "aliases": ["the Pale Warden", "Zhaerith"]},
            {"canonical_name": "  ", "aliases": None},
            "not-an-entity",
            {"canonical_name": "x" * 500},
        ]
    }

    assert build_phrase_hints(snapshot) == ["Zhaerith", "the Pale Warden"]


def test_build_phrase_hints_without_entities_is_empty() -> None:
    assert build_phrase_hints({}) == []


def test_build_phrase_hints_respects_configured_cap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "speech_to_text_max_phrase_hints", 2)
    snapshot = {"entities": [{"canonical_name": f"Name{i}"} for i in range(5)]}

    assert build_phrase_hints(snapshot) == ["Name0", "Name1"]
