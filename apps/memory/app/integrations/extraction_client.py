"""Extraction backend contract and the factory that picks the configured provider."""

from typing import Protocol

from app.config import Settings
from app.integrations.anthropic_extraction_client import AnthropicExtractionClient
from app.integrations.muse_extraction_client import MuseExtractionClient
from app.models.extraction import ExtractionResult, SupersessionJudgeResult


class ExtractionBackend(Protocol):
    @property
    def model_name(self) -> str: ...

    async def extract(
        self, system_prompt: str, user_content: str
    ) -> ExtractionResult: ...

    async def judge_supersessions(
        self, system_prompt: str, user_content: str
    ) -> SupersessionJudgeResult: ...


def _build_muse_client(settings: Settings) -> MuseExtractionClient | None:
    key = settings.extraction_api_key
    secret = key.get_secret_value() if key is not None else ""
    if not secret.strip():
        return None
    return MuseExtractionClient(
        api_key=secret,
        base_url=settings.muse_base_url,
        model_name=settings.extraction_model_name,
        timeout_seconds=settings.muse_extraction_timeout_seconds,
        max_tokens=settings.muse_extraction_max_tokens,
        reasoning_effort=(
            settings.extraction_thinking_level
            or settings.muse_extraction_reasoning_effort
        ),
    )


def build_extraction_client(settings: Settings) -> ExtractionBackend | None:
    if settings.extraction_provider == "anthropic":
        return AnthropicExtractionClient(
            model_name=settings.anthropic_extraction_model_name,
            timeout_seconds=settings.extraction_client_timeout_seconds,
            max_tokens=settings.anthropic_extraction_max_tokens,
            effort=settings.anthropic_extraction_effort,
            project=settings.vertex_project,
            location=settings.vertex_location,
        )
    return _build_muse_client(settings)
