"""Pydantic response shape for the voice transcription endpoint."""

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    transcript: str
