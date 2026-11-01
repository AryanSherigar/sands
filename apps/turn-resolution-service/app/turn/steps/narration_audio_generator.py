"""Generates narration audio for a turn via Gemini TTS.

A missing narration audio must never fail or degrade a turn -- this module
never raises into the pipeline (mirrors scene_image_generator.py's
swallow-and-log best-effort pattern).
"""

import asyncio
import io
import json
import re
import uuid
import wave

import structlog
from app.exceptions.turn_exceptions import SceneImageGenerationError
from app.exceptions.voice_exceptions import NarrationAudioGenerationError
from app.integrations import speech_client, storage_client
from app.turn import speaker_voice_pool
from app.turn.speaker_tags import NARRATOR_SPEAKER, SpeakerSpan, parse_speaker_spans
from app.turn.steps.state_writer import NarrationAudioResult
from google.genai import errors as genai_errors

logger = structlog.get_logger()

EVENT_NARRATION_AUDIO_GENERATION_FAILED = "narration_audio_generation_failed"

_MAX_VOICES_PER_TURN = 2
_MAX_TIMED_SEGMENTS = 8
_DEFAULT_SAMPLE_RATE = 24000
_SAMPLE_RATE_PATTERN = re.compile(r"rate=(\d+)")


def find_speaker_voice_map(
    spans: list[SpeakerSpan],
    narrator_voice: str,
    npc_voice_pool: tuple[str, ...],
) -> tuple[list[SpeakerSpan], dict[str, str]]:
    """Resolve the narrator voice plus at most one NPC voice for this turn.

    Gemini's TTS API allows exactly one or two speaker voices per request.
    When the tagged spans name 2+ distinct NPCs, this collapses the whole
    turn to a single narrator-only span/voice rather than picking one NPC
    arbitrarily -- every voice always gets heard equally, or none does.
    """
    npc_names = {span.speaker for span in spans if span.speaker != NARRATOR_SPEAKER}
    if len(npc_names) >= _MAX_VOICES_PER_TURN:
        return _collapse_to_narrator_only(spans, narrator_voice)

    voice_map = {NARRATOR_SPEAKER: narrator_voice}
    if npc_names:
        (npc_name,) = npc_names
        voice_map[npc_name] = speaker_voice_pool.resolve_npc_voice(
            npc_name, npc_voice_pool
        )
    return spans, voice_map


def _collapse_to_narrator_only(
    spans: list[SpeakerSpan], narrator_voice: str
) -> tuple[list[SpeakerSpan], dict[str, str]]:
    collapsed_text = "\n\n".join(span.text for span in spans if span.text)
    collapsed_spans = [SpeakerSpan(NARRATOR_SPEAKER, collapsed_text)]
    return collapsed_spans, {NARRATOR_SPEAKER: narrator_voice}


def _parse_sample_rate(mime_type: str) -> int:
    match = _SAMPLE_RATE_PATTERN.search(mime_type)
    return int(match.group(1)) if match else _DEFAULT_SAMPLE_RATE


def _wrap_pcm_as_wav(pcm_bytes: bytes, mime_type: str) -> bytes:
    """Prepend a standard RIFF/WAVE header to Gemini TTS's raw 16-bit mono
    PCM output, using the sample rate mime_type encodes (e.g.
    "audio/L16;rate=24000") rather than a hardcoded assumption."""
    sample_rate = _parse_sample_rate(mime_type)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


async def generate_narration_audio(
    raw_tagged_text: str,
    narrator_voice: str,
    npc_voice_pool: tuple[str, ...],
    timeout_seconds: int,
    *,
    capture_speaker_timing: bool = False,
) -> NarrationAudioResult | None:
    """Generate and upload this turn's narration audio.

    Returns None on any failure, or when there's no text to synthesize --
    this step never raises into the pipeline.
    """
    spans = parse_speaker_spans(raw_tagged_text)
    if not spans:
        return None
    resolved_spans, voice_map = find_speaker_voice_map(
        spans, narrator_voice, npc_voice_pool
    )
    try:
        if (
            capture_speaker_timing
            and len(resolved_spans) <= _MAX_TIMED_SEGMENTS
            and any(span.speaker != NARRATOR_SPEAKER for span in resolved_spans)
        ):
            audio_url = await asyncio.wait_for(
                _synthesize_timed_audio(resolved_spans, voice_map, timeout_seconds),
                timeout=timeout_seconds,
            )
        else:
            audio_url = await _synthesize_and_upload(
                resolved_spans, voice_map, timeout_seconds
            )
    except (
        NarrationAudioGenerationError,
        SceneImageGenerationError,
        genai_errors.ClientError,
        TimeoutError,
    ):
        logger.warning(EVENT_NARRATION_AUDIO_GENERATION_FAILED, exc_info=True)
        return None
    return NarrationAudioResult(audio_url)


async def _synthesize_timed_audio(
    spans: list[SpeakerSpan], voice_map: dict[str, str], timeout_seconds: int
) -> str:
    chunks: list[bytes] = []
    segments: list[dict[str, object]] = []
    rate: int | None = None
    samples = 0
    for span in spans:
        pcm, mime = await speech_client.synthesize_narration_audio(
            [span], voice_map, timeout_seconds
        )
        current_rate = _parse_sample_rate(mime)
        if len(pcm) % 2 or (rate is not None and current_rate != rate):
            raise NarrationAudioGenerationError("Incompatible audio segments")
        rate = current_rate
        end = samples + len(pcm) // 2
        if span.speaker != NARRATOR_SPEAKER:
            segments.append(
                {"speaker": span.speaker, "start": samples / rate, "end": end / rate}
            )
        samples = end
        chunks.append(pcm)
    key = f"narration-audio/{uuid.uuid4()}.wav"
    audio_url = await storage_client.upload_image(
        _wrap_pcm_as_wav(b"".join(chunks), f"rate={rate}"), "audio/wav", key
    )
    try:
        await storage_client.upload_image(
            json.dumps({"segments": segments}).encode(),
            "application/json",
            f"{key}.speakers.json",
        )
    except SceneImageGenerationError:
        logger.warning("narration_speaker_timing_upload_failed", exc_info=True)
    return audio_url


async def _synthesize_and_upload(
    spans: list[SpeakerSpan],
    voice_map: dict[str, str],
    timeout_seconds: int,
) -> str:
    pcm_bytes, mime_type = await speech_client.synthesize_narration_audio(
        spans, voice_map, timeout_seconds
    )
    wav_bytes = _wrap_pcm_as_wav(pcm_bytes, mime_type)
    object_key = f"narration-audio/{uuid.uuid4()}.wav"
    return await storage_client.upload_image(wav_bytes, "audio/wav", object_key)
