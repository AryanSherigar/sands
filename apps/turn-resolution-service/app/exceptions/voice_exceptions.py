"""Voice transcription domain exception classes."""

from app.exceptions.base import BaseAppException


class AudioValidationError(BaseAppException):
    """Raised when uploaded audio fails content-type, size, or presence validation."""

    def __init__(self, message: str = "Invalid audio upload"):
        super().__init__(message=message, status_code=400)


class TranscriptionUnavailableError(BaseAppException):
    """Raised when Speech-to-Text is transiently unavailable (timeout, 5xx, rate limit)."""

    def __init__(self, message: str = "Voice transcription is temporarily unavailable"):
        super().__init__(message=message, status_code=502)


class NarrationAudioGenerationError(BaseAppException):
    """Raised when narration audio synthesis is transiently unavailable
    (timeout, 5xx, rate limit) -- caught and swallowed by
    narration_audio_generator.py, since missing narration audio must never
    fail or degrade a turn."""

    def __init__(self, message: str = "Narration audio generation failed"):
        super().__init__(message=message, status_code=502)


class UnsupportedAudioFormatError(BaseAppException):
    """Raised when the recorded audio's format has no Speech-to-Text decoding
    path — not retryable, so the UI can turn this into a "voice unavailable"
    state instead of asking the player to try again."""

    def __init__(
        self,
        message: str = "This browser's audio format isn't supported for transcription",
    ):
        super().__init__(message=message, status_code=415)


class WelcomePlaythroughNotFoundError(BaseAppException):
    def __init__(self, message: str = "Playthrough not found") -> None:
        super().__init__(message=message, status_code=404)
