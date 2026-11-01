"""Speech I/O integration boundary for Turn Resolution Service: Meta Muse Voice
Transcribe for voice input, Gemini native TTS for voice output.

Voice input goes to Muse's REST transcription endpoint, which accepts only mono
16-bit PCM WAV, so recordings are decoded first (audio_transcoder.py). Muse has no
text-to-speech, so voice output stays on Vertex AI's genai SDK through a private
genai.Client authenticated with the same Express Mode api_key as before.

For the transcription path: the only file app/services/voice_service.py is
permitted to call. For the narration-audio synthesis path: the only file
app/turn/steps/narration_audio_generator.py is permitted to call (a turn
pipeline step occupies the service layer's position in the turn loop per
CLAUDE.md).
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import structlog
from app.config import settings
from app.exceptions.voice_exceptions import (
    NarrationAudioGenerationError,
    TranscriptionUnavailableError,
)
from app.integrations import audio_transcoder
from app.turn.speaker_tags import NARRATOR_SPEAKER, SpeakerSpan
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from google.oauth2 import service_account

logger = structlog.get_logger()

EVENT_TRANSCRIBE_ERROR = "speech_to_text_transcribe_error"
EVENT_SYNTHESIZE_ERROR = "text_to_speech_synthesize_error"

_RATE_LIMIT_STATUS_CODE = 429
_MUSE_AUDIO_ENCODING = "WAV"
_MUSE_TRANSCRIBE_MODE = "PUSH_TO_TALK"
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_tts_client: genai.Client | None = None


def _load_service_account_credentials(
    scopes: list[str] | None = None,
) -> service_account.Credentials | None:
    cred_path = settings.speech_to_text_credentials_path
    if not (cred_path and os.path.isfile(cred_path)):
        return None
    return service_account.Credentials.from_service_account_file(
        cred_path, scopes=scopes
    )


def _transcription_files(
    wav_bytes: bytes, phrase_hints: list[str]
) -> dict[str, tuple[str | None, str | bytes, str]]:
    request_part: dict[str, object] = {
        "model": settings.muse_voice_model_name,
        "audioEncoding": _MUSE_AUDIO_ENCODING,
        "mode": _MUSE_TRANSCRIBE_MODE,
    }
    if phrase_hints:
        request_part["keywords"] = phrase_hints
    return {
        "request": (None, json.dumps(request_part), "application/json"),
        "audio": ("audio.wav", wav_bytes, "audio/wav"),
    }


async def transcribe_audio(
    content: bytes,
    content_type: str,
    timeout_seconds: int,
    phrase_hints: list[str] | None = None,
) -> str:
    """Transcribe a short player-recorded action clip.

    Empty transcript (no speech detected) is a valid, non-error result --
    returns "" rather than raising, so the caller/UI can show "didn't catch
    that" without treating it as a service failure. phrase_hints bias
    recognition toward scenario-specific names and terms.
    """
    wav_bytes = await audio_transcoder.to_mono_wav(content)
    files = _transcription_files(wav_bytes, phrase_hints or [])
    headers = {"Authorization": f"Bearer {settings.muse_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as http_client:
            response = await http_client.post(
                f"{settings.muse_base_url}/asr/transcribe", files=files, headers=headers
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            EVENT_TRANSCRIBE_ERROR,
            status_code=exc.response.status_code,
            content_type=content_type,
        )
        raise TranscriptionUnavailableError() from exc
    except httpx.TransportError as exc:
        logger.warning(
            EVENT_TRANSCRIBE_ERROR,
            error_type=type(exc).__name__,
            content_type=content_type,
        )
        raise TranscriptionUnavailableError() from exc
    transcript = response.json().get("transcript")
    return transcript.strip() if isinstance(transcript, str) else ""


def _get_tts_client() -> genai.Client:
    """Build the Vertex AI (API key / Express Mode) TTS client lazily, same
    construction pattern the narration client used."""
    global _tts_client
    if _tts_client is None:
        _tts_client = _build_tts_client()
    return _tts_client


def _build_tts_client() -> genai.Client:
    credentials = _load_service_account_credentials(scopes=[_CLOUD_PLATFORM_SCOPE])
    if settings.should_use_service_account_for_tts and credentials is not None:
        return genai.Client(
            vertexai=True,
            project=settings.speech_to_text_project_id,
            location=settings.text_to_speech_location,
            credentials=credentials,
        )
    return genai.Client(vertexai=True, api_key=settings.gemini_api_key)


def _build_speech_config(speaker_voice_map: dict[str, str]) -> types.SpeechConfig:
    """A single-speaker VoiceConfig for narrator-only audio, or a
    MultiSpeakerVoiceConfig for narrator+NPC. The SDK requires exactly two
    speaker configs when using multi-speaker mode, so a narrator-only map
    must take the single-speaker branch, never multi-speaker with one entry
    padded out."""
    if len(speaker_voice_map) == 1:
        (voice_name,) = speaker_voice_map.values()
        return types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
    speaker_configs = [
        types.SpeakerVoiceConfig(
            speaker=_prompt_speaker_label(speaker),
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            ),
        )
        for speaker, voice_name in speaker_voice_map.items()
    ]
    return types.SpeechConfig(
        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=speaker_configs
        )
    )


def _prompt_speaker_label(speaker: str) -> str:
    """The label used both as the multi-speaker config's speaker name and
    as the prefix on each line of the synthesis prompt -- Gemini's
    documented contract requires these to match exactly."""
    return "Narrator" if speaker == NARRATOR_SPEAKER else speaker


def _build_synthesis_prompt(spans: list[SpeakerSpan]) -> str:
    return "\n".join(
        f"{_prompt_speaker_label(span.speaker)}: {span.text}"
        for span in spans
        if span.text
    )


def _extract_pcm_audio(response: types.GenerateContentResponse) -> tuple[bytes, str]:
    """Returns (pcm_bytes, mime_type). mime_type typically encodes the
    sample rate (e.g. "audio/L16;rate=24000") -- the caller parses it rather
    than trusting a hardcoded default."""
    candidates = response.candidates or []
    parts = candidates[0].content.parts if candidates and candidates[0].content else []
    for part in parts or []:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data, part.inline_data.mime_type or ""
    raise NarrationAudioGenerationError("Gemini TTS response carried no audio data")


async def synthesize_narration_audio(
    spans: list[SpeakerSpan],
    speaker_voice_map: dict[str, str],
    timeout_seconds: int,
) -> tuple[bytes, str]:
    """Synthesize this turn's narration+dialogue as speech via Gemini native
    TTS. Returns (pcm_bytes, mime_type) -- caller wraps the PCM as a WAV
    file using the sample rate encoded in mime_type."""
    prompt = _build_synthesis_prompt(spans)
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=_build_speech_config(speaker_voice_map),
    )
    try:
        response = await asyncio.wait_for(
            _get_tts_client().aio.models.generate_content(
                model=settings.text_to_speech_model, contents=prompt, config=config
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.warning(EVENT_SYNTHESIZE_ERROR, error_type="TimeoutError")
        raise NarrationAudioGenerationError() from exc
    except genai_errors.ServerError as exc:
        logger.warning(EVENT_SYNTHESIZE_ERROR, error_type="ServerError")
        raise NarrationAudioGenerationError() from exc
    except genai_errors.ClientError as exc:
        error_type = (
            "RateLimitError" if exc.code == _RATE_LIMIT_STATUS_CODE else "ClientError"
        )
        logger.warning(EVENT_SYNTHESIZE_ERROR, error_type=error_type)
        raise NarrationAudioGenerationError() from exc
    return _extract_pcm_audio(response)


async def synthesize_welcome_closing(text: str) -> bytes:
    """Synthesize the fixed welcome closing with the configured Katie voice."""
    if not settings.fish_api_key:
        raise NarrationAudioGenerationError("Welcome voice is unavailable")
    try:
        return await asyncio.wait_for(
            _request_welcome_audio(text), settings.fish_timeout_seconds
        )
    except (httpx.HTTPError, asyncio.TimeoutError) as error:
        logger.warning("welcome_voice_unavailable", error_type=type(error).__name__)
        raise NarrationAudioGenerationError() from error


async def _request_welcome_audio(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=settings.fish_timeout_seconds) as client:
        response = await client.post(
            "https://api.fish.audio/v1/tts",
            headers=_welcome_headers(),
            json=_welcome_payload(text),
        )
        response.raise_for_status()
        return response.content


def _welcome_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.fish_api_key}",
        "model": settings.fish_tts_model,
    }


def _welcome_payload(text: str) -> dict[str, object]:
    return {
        "text": text,
        "reference_id": settings.fish_katie_voice_id,
        "format": "wav",
        "sample_rate": 44100,
        "temperature": 0.45,
        "prosody": {"speed": 0.9, "normalize_loudness": True},
    }
