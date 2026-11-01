"""Sensory cue SSE payload (tool `atmosphere`)."""

from pydantic import BaseModel

DEFAULT_SILENCE_DURATION_MS = 800


class FiredCue(BaseModel):
    """One cue the client performs: cut the ambience, hold the silence, play
    the sound, bring the ambience back."""

    cue: str
    cut_ambient: bool = True
    silence_duration_ms: int = DEFAULT_SILENCE_DURATION_MS
