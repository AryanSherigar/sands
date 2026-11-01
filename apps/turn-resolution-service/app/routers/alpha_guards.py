from app.config import settings
from app.exceptions.alpha_exceptions import AlphaFeatureDisabledError, AlphaPausedError


async def forbid_in_alpha_mode() -> None:
    if settings.is_alpha_mode:
        raise AlphaFeatureDisabledError()


async def forbid_when_turns_suspended() -> None:
    if settings.is_turns_suspended:
        raise AlphaPausedError()
