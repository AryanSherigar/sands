import asyncio
import uuid

from app.config import (
    WELCOME_NAME_MAX_LENGTH as NAME_MAX_LENGTH,
)
from app.config import (
    WELCOME_NAME_PUNCTUATION as NAME_PUNCTUATION,
)
from app.config import (
    WELCOME_TAPE_ID as TAPE_ID,
)
from app.db.models.playthrough import Playthrough
from app.exceptions.voice_exceptions import (
    AudioValidationError,
    WelcomePlaythroughNotFoundError,
)
from app.integrations.speech_client import synthesize_welcome_closing
from app.repositories.playthrough_repo import PlaythroughRepo
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from app.services.welcome_audio import treat_welcome_audio
from sqlalchemy.ext.asyncio import AsyncSession


def get_welcome_name(playthrough: Playthrough, user_id: uuid.UUID) -> str:
    if playthrough.created_by != user_id:
        raise WelcomePlaythroughNotFoundError()
    world = playthrough.scenario_snapshot.get("world_data", {})
    presentation = world.get("presentation", {}) if isinstance(world, dict) else {}
    if (
        not isinstance(presentation, dict)
        or presentation.get("welcome_tape_id") != TAPE_ID
    ):
        raise AudioValidationError("This scenario has no welcome tape")
    if playthrough.status != "active" or playthrough.turn_count != 0:
        raise AudioValidationError(
            "Welcome tape is only available before the first turn"
        )
    setup = playthrough.state.get("setup", {})
    name = setup.get("character_name") if isinstance(setup, dict) else None
    if not isinstance(name, str) or not is_supported_name(name):
        raise AudioValidationError("Name cannot be spoken")
    return name.strip()


def is_supported_name(name: str) -> bool:
    return (
        0 < len(name.strip()) <= NAME_MAX_LENGTH
        and any(character.isalpha() for character in name)
        and all(
            character.isalpha() or character in NAME_PUNCTUATION for character in name
        )
    )


async def generate_welcome_closing(
    playthrough_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    quota_service: QuotaService,
) -> bytes:
    playthrough = await PlaythroughRepo(session).get_by_id(playthrough_id)
    if playthrough is None:
        raise WelcomePlaythroughNotFoundError()
    name = get_welcome_name(playthrough, user_id)
    async with quota_service.reserved(QuotaFeature.TTS_NARRATION, user_id):
        content = await synthesize_welcome_closing(
            f"Thank you for your service, {name}."
        )
        return await asyncio.get_running_loop().run_in_executor(
            None, treat_welcome_audio, content
        )
