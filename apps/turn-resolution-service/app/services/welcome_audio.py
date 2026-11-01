import io
import wave

import numpy as np
from app.config import (
    WELCOME_ACTIVE_THRESHOLD,
    WELCOME_FILTER_ORDER,
    WELCOME_HIGH_PASS_HZ,
    WELCOME_LOW_PASS_HZ,
    WELCOME_PEAK_LIMIT,
    WELCOME_TAPE_DRIVE,
    WELCOME_WOW_HZ,
    WELCOME_WOW_SAMPLES,
)
from app.config import (
    WELCOME_MAX_AUDIO_SECONDS as MAX_SECONDS,
)
from app.config import (
    WELCOME_PCM_SCALE as PCM_SCALE,
)
from app.config import (
    WELCOME_SAMPLE_RATE as SAMPLE_RATE,
)
from app.config import (
    WELCOME_VOICE_RMS as VOICE_RMS,
)
from app.exceptions.voice_exceptions import NarrationAudioGenerationError


def treat_welcome_audio(content: bytes) -> bytes:
    try:
        samples = read_samples(content)
        treated = filter_samples(samples)
        return encode_samples(treated)
    except (wave.Error, EOFError, ValueError) as error:
        raise NarrationAudioGenerationError("Invalid welcome audio") from error


def read_samples(content: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(content), "rb") as source:
        if source.getsampwidth() != 2 or source.getframerate() != SAMPLE_RATE:
            raise ValueError("Unsupported audio format")
        raw = source.readframes(SAMPLE_RATE * MAX_SECONDS + 1)
        samples = np.frombuffer(raw, dtype="<i2")
        samples = samples.reshape(-1, source.getnchannels()).mean(axis=1) / PCM_SCALE
    if not len(samples) or len(samples) > SAMPLE_RATE * MAX_SECONDS:
        raise ValueError("Invalid audio duration")
    return samples


def filter_samples(samples: np.ndarray) -> np.ndarray:
    frequencies = np.fft.rfftfreq(len(samples), 1 / SAMPLE_RATE)
    response = frequencies**2 / (frequencies**2 + WELCOME_HIGH_PASS_HZ**2)
    response /= np.sqrt(1 + (frequencies / WELCOME_LOW_PASS_HZ) ** WELCOME_FILTER_ORDER)
    filtered = np.fft.irfft(np.fft.rfft(samples) * response, n=len(samples))
    active = filtered[np.abs(filtered) > WELCOME_ACTIVE_THRESHOLD]
    if not len(active):
        raise ValueError("Silent audio")
    gain = VOICE_RMS / np.sqrt(np.mean(active**2))
    saturated = np.tanh(filtered * gain * WELCOME_TAPE_DRIVE) / WELCOME_TAPE_DRIVE
    positions = np.arange(len(samples))
    drift = WELCOME_WOW_SAMPLES * np.sin(
        2 * np.pi * WELCOME_WOW_HZ * positions / SAMPLE_RATE
    )
    return np.clip(
        np.interp(positions + drift, positions, saturated),
        -WELCOME_PEAK_LIMIT,
        WELCOME_PEAK_LIMIT,
    )


def encode_samples(samples: np.ndarray) -> bytes:
    destination = io.BytesIO()
    with wave.open(destination, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes((samples * (PCM_SCALE - 1)).astype("<i2").tobytes())
    return destination.getvalue()
