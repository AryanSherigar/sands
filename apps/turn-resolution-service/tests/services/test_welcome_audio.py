import io
import wave

import numpy as np
import pytest
from app.exceptions.voice_exceptions import NarrationAudioGenerationError
from app.services.welcome_audio import treat_welcome_audio
from app.services.welcome_service import is_supported_name


def make_wave(samples: np.ndarray) -> bytes:
    destination = io.BytesIO()
    with wave.open(destination, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes((samples * 32767).astype("<i2").tobytes())
    return destination.getvalue()


def test_tape_treatment_preserves_duration_and_limits_peaks() -> None:
    original = np.sin(np.arange(44100) * 2 * np.pi * 440 / 44100) * 0.8
    treated = treat_welcome_audio(make_wave(original))
    with wave.open(io.BytesIO(treated), "rb") as audio:
        assert audio.getnframes() == len(original)
        assert audio.getframerate() == 44100
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
    assert 0 < np.abs(samples).max() < 32767


@pytest.mark.parametrize("content", [b"not audio", make_wave(np.zeros(44100))])
def test_invalid_or_silent_audio_is_rejected(content: bytes) -> None:
    with pytest.raises(NarrationAudioGenerationError):
        treat_welcome_audio(content)


@pytest.mark.parametrize(
    "name", ["Alex", "Jean-Luc", "O'Connor", "Aryan Sherigar", "Zoë"]
)
def test_supported_names(name: str) -> None:
    assert is_supported_name(name)


@pytest.mark.parametrize(
    "name", ["", " ", "[laughing] Alex", "<|speaker:1|>", "Alex\n", "a" * 61]
)
def test_unsupported_names(name: str) -> None:
    assert not is_supported_name(name)
