"""Unit tests for audio_transcoder.py; audio is synthesized in-process with PyAV."""

import io
import wave
from fractions import Fraction

import av
import numpy as np
import pytest
from app.exceptions.voice_exceptions import AudioValidationError
from app.integrations import audio_transcoder

_SOURCE_RATE = 48000
_SECONDS = 1.0


def _encode(container_format: str, codec: str) -> bytes:
    buffer = io.BytesIO()
    with av.open(buffer, mode="w", format=container_format) as container:
        stream = container.add_stream(codec, rate=_SOURCE_RATE)
        stream.layout = "mono"
        samples = np.sin(
            2 * np.pi * 440 * np.arange(int(_SOURCE_RATE * _SECONDS)) / _SOURCE_RATE
        )
        pcm = (samples * 12000).astype(np.int16).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(pcm, format="s16", layout="mono")
        frame.sample_rate = _SOURCE_RATE
        frame.time_base = Fraction(1, _SOURCE_RATE)
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return buffer.getvalue()


def _read_wav(content: bytes) -> tuple[int, int, int, float]:
    with wave.open(io.BytesIO(content)) as wav:
        frames = wav.getnframes()
        return (
            wav.getnchannels(),
            wav.getsampwidth(),
            wav.getframerate(),
            (frames / wav.getframerate()),
        )


@pytest.mark.parametrize(
    ("container_format", "codec"), [("webm", "libopus"), ("ogg", "libopus")]
)
async def test_to_mono_wav_converts_compressed_audio(
    container_format: str, codec: str
) -> None:
    source = _encode(container_format, codec)

    wav_bytes = await audio_transcoder.to_mono_wav(source)

    channels, sample_width, rate, duration = _read_wav(wav_bytes)
    assert channels == 1
    assert sample_width == 2
    assert rate == 16000
    assert duration == pytest.approx(_SECONDS, abs=0.2)


async def test_to_mono_wav_rejects_undecodable_bytes() -> None:
    with pytest.raises(AudioValidationError):
        await audio_transcoder.to_mono_wav(b"this is not audio at all")
