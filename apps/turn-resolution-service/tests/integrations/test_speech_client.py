"""Unit tests for the real speech_client.py, with the Muse endpoint
and the genai TTS client mocked."""

import asyncio
import io
import json
import wave

import httpx
import pytest
import respx
from app.config import settings
from app.exceptions.voice_exceptions import (
    NarrationAudioGenerationError,
    TranscriptionUnavailableError,
)
from app.integrations import speech_client
from app.turn.speaker_tags import NARRATOR_SPEAKER, SpeakerSpan
from google.genai import errors as genai_errors
from google.genai import types


class _FakeAioModels:
    def __init__(self, generate_content) -> None:
        self._generate_content = generate_content

    async def generate_content(self, *, model, contents, config):
        return await self._generate_content(
            model=model, contents=contents, config=config
        )


class _FakeAio:
    def __init__(self, generate_content) -> None:
        self.models = _FakeAioModels(generate_content)


class _FakeGenaiClient:
    def __init__(self, generate_content) -> None:
        self.aio = _FakeAio(generate_content)


def _install_fake_tts_client(monkeypatch, generate_content) -> None:
    monkeypatch.setattr(
        speech_client, "_tts_client", _FakeGenaiClient(generate_content)
    )


def _fake_audio_response(data: bytes, mime_type: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(data=data, mime_type=mime_type)
                        )
                    ]
                )
            )
        ]
    )


async def test_synthesize_narration_audio_returns_pcm_and_mime_type(
    monkeypatch,
) -> None:
    async def fake_generate_content(*, model, contents, config):
        return _fake_audio_response(b"\x00\x01raw-pcm", "audio/L16;rate=24000")

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [SpeakerSpan(NARRATOR_SPEAKER, "You creep through the door.")]
    pcm_bytes, mime_type = await speech_client.synthesize_narration_audio(
        spans, {NARRATOR_SPEAKER: "Kore"}, 5
    )

    assert pcm_bytes == b"\x00\x01raw-pcm"
    assert mime_type == "audio/L16;rate=24000"


async def test_synthesize_narration_audio_single_speaker_uses_voice_config(
    monkeypatch,
) -> None:
    captured = {}

    async def fake_generate_content(*, model, contents, config):
        captured["config"] = config
        captured["prompt"] = contents
        return _fake_audio_response(b"pcm", "audio/L16;rate=24000")

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [SpeakerSpan(NARRATOR_SPEAKER, "You creep through the door.")]
    await speech_client.synthesize_narration_audio(spans, {NARRATOR_SPEAKER: "Kore"}, 5)

    speech_config = captured["config"].speech_config
    assert speech_config.voice_config.prebuilt_voice_config.voice_name == "Kore"
    assert speech_config.multi_speaker_voice_config is None
    assert captured["prompt"] == "Narrator: You creep through the door."


async def test_synthesize_narration_audio_two_speakers_uses_multi_speaker_config(
    monkeypatch,
) -> None:
    captured = {}

    async def fake_generate_content(*, model, contents, config):
        captured["config"] = config
        return _fake_audio_response(b"pcm", "audio/L16;rate=24000")

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [
        SpeakerSpan(NARRATOR_SPEAKER, "You creep through the door."),
        SpeakerSpan("Grimjaw", "Get out."),
    ]
    await speech_client.synthesize_narration_audio(
        spans, {NARRATOR_SPEAKER: "Kore", "Grimjaw": "Puck"}, 5
    )

    multi_config = captured["config"].speech_config.multi_speaker_voice_config
    assert multi_config is not None
    speakers = {
        c.speaker: c.voice_config.prebuilt_voice_config.voice_name
        for c in multi_config.speaker_voice_configs
    }
    assert speakers == {"Narrator": "Kore", "Grimjaw": "Puck"}


async def test_synthesize_narration_audio_timeout_raises_narration_audio_generation_error(
    monkeypatch,
) -> None:
    async def fake_generate_content(*, model, contents, config):
        await asyncio.sleep(0.05)
        return _fake_audio_response(b"pcm", "audio/L16;rate=24000")

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [SpeakerSpan(NARRATOR_SPEAKER, "text")]
    with pytest.raises(NarrationAudioGenerationError):
        await speech_client.synthesize_narration_audio(
            spans, {NARRATOR_SPEAKER: "Kore"}, 0
        )


async def test_synthesize_narration_audio_server_error_raises(monkeypatch) -> None:
    async def fake_generate_content(*, model, contents, config):
        raise genai_errors.ServerError(500, {"error": {"message": "unavailable"}})

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [SpeakerSpan(NARRATOR_SPEAKER, "text")]
    with pytest.raises(NarrationAudioGenerationError):
        await speech_client.synthesize_narration_audio(
            spans, {NARRATOR_SPEAKER: "Kore"}, 5
        )


async def test_synthesize_narration_audio_no_audio_part_raises(monkeypatch) -> None:
    async def fake_generate_content(*, model, contents, config):
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(parts=[]))]
        )

    _install_fake_tts_client(monkeypatch, fake_generate_content)

    spans = [SpeakerSpan(NARRATOR_SPEAKER, "text")]
    with pytest.raises(NarrationAudioGenerationError):
        await speech_client.synthesize_narration_audio(
            spans, {NARRATOR_SPEAKER: "Kore"}, 5
        )


def test_build_tts_client_uses_api_key_by_default(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        speech_client.genai, "Client", lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(
        speech_client.settings, "should_use_service_account_for_tts", False
    )
    monkeypatch.setattr(speech_client.settings, "gemini_api_key", "test-key")

    speech_client._build_tts_client()

    assert captured == {"vertexai": True, "api_key": "test-key"}


def test_build_tts_client_uses_service_account_when_enabled(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_credentials = object()
    monkeypatch.setattr(
        speech_client.genai, "Client", lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(
        speech_client,
        "_load_service_account_credentials",
        lambda scopes=None: fake_credentials,
    )
    monkeypatch.setattr(
        speech_client.settings, "should_use_service_account_for_tts", True
    )
    monkeypatch.setattr(
        speech_client.settings, "speech_to_text_project_id", "test-project"
    )
    monkeypatch.setattr(speech_client.settings, "text_to_speech_location", "global")

    speech_client._build_tts_client()

    assert captured == {
        "vertexai": True,
        "project": "test-project",
        "location": "global",
        "credentials": fake_credentials,
    }


_MUSE_ASR_URL = "https://api.meta.ai/v1/asr/transcribe"


def _wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)
    return buffer.getvalue()


@pytest.fixture
def muse_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "muse_api_key", "test-key")
    monkeypatch.setattr(settings, "muse_base_url", "https://api.meta.ai/v1")


@respx.mock
async def test_muse_transcribe_returns_transcript_and_sends_request_part(
    muse_provider,
) -> None:
    route = respx.post(_MUSE_ASR_URL).mock(
        return_value=httpx.Response(
            200, json={"sessionId": "s", "transcript": "  I open the door. "}
        )
    )

    result = await speech_client.transcribe_audio(
        _wav_bytes(), "audio/wav", 5, phrase_hints=["Mara Voss", "Salt Row"]
    )

    assert result == "I open the door."
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-key"
    body = request.content
    assert b'name="request"' in body
    assert b'name="audio"' in body
    sent = json.loads(
        body.split(b'name="request"')[1].split(b"\r\n\r\n")[1].split(b"\r\n--")[0]
    )
    assert sent["model"] == "muse-voice-transcribe-1.0"
    assert sent["audioEncoding"] == "WAV"
    assert sent["keywords"] == ["Mara Voss", "Salt Row"]


@respx.mock
async def test_muse_transcribe_omits_keywords_without_hints(muse_provider) -> None:
    route = respx.post(_MUSE_ASR_URL).mock(
        return_value=httpx.Response(200, json={"transcript": "hello"})
    )

    await speech_client.transcribe_audio(_wav_bytes(), "audio/wav", 5)

    assert b"keywords" not in route.calls.last.request.content


@respx.mock
async def test_muse_transcribe_missing_transcript_returns_empty(muse_provider) -> None:
    respx.post(_MUSE_ASR_URL).mock(return_value=httpx.Response(200, json={"turns": []}))

    assert await speech_client.transcribe_audio(_wav_bytes(), "audio/wav", 5) == ""


@respx.mock
@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
async def test_muse_transcribe_error_status_raises_unavailable(
    muse_provider, status_code: int
) -> None:
    respx.post(_MUSE_ASR_URL).mock(return_value=httpx.Response(status_code))

    with pytest.raises(TranscriptionUnavailableError):
        await speech_client.transcribe_audio(_wav_bytes(), "audio/wav", 5)


@respx.mock
async def test_muse_transcribe_timeout_raises_unavailable(muse_provider) -> None:
    respx.post(_MUSE_ASR_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(TranscriptionUnavailableError):
        await speech_client.transcribe_audio(_wav_bytes(), "audio/wav", 5)
