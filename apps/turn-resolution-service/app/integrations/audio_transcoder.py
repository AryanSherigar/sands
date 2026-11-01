"""Decodes browser-recorded audio into the mono 16-bit WAV that Muse Voice
Transcribe's REST endpoint requires. Used only by speech_client.py."""

from __future__ import annotations

import asyncio
import io
import wave

import av
from app.exceptions.voice_exceptions import AudioValidationError

TARGET_SAMPLE_RATE = 16000
_SAMPLE_WIDTH_BYTES = 2


def _decode_to_pcm(content: bytes) -> bytes:
    resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_SAMPLE_RATE)
    pcm = bytearray()
    with av.open(io.BytesIO(content)) as container:
        if not container.streams.audio:
            raise AudioValidationError("No audio track found")
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                pcm += resampled.to_ndarray().tobytes()
    for resampled in resampler.resample(None):
        pcm += resampled.to_ndarray().tobytes()
    return bytes(pcm)


def _wrap_in_wav(pcm: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(_SAMPLE_WIDTH_BYTES)
        wav.setframerate(TARGET_SAMPLE_RATE)
        wav.writeframes(pcm)
    return buffer.getvalue()


def _transcode(content: bytes) -> bytes:
    try:
        pcm = _decode_to_pcm(content)
    except av.error.FFmpegError as exc:
        raise AudioValidationError("Unsupported or corrupt audio") from exc
    return _wrap_in_wav(pcm)


async def to_mono_wav(content: bytes) -> bytes:
    """Any container PyAV can decode (webm/opus, ogg, mp4, wav, mp3) to 16 kHz mono WAV."""
    return await asyncio.get_running_loop().run_in_executor(None, _transcode, content)
