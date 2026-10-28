"""Effects a condition asks the browser to perform once, after the turn, and the
image it can attach to that turn. Both live in the condition's metadata."""

from typing import Literal

from app.config import settings
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

METADATA_CLIENT_EFFECT = "client_effect"
METADATA_AUTHORED_IMAGE_URL = "authored_image_url"
MAX_TAKEOVER_TEXT_LENGTH = 80
LOCAL_UPLOADS_PATH = "/uploads/"


class InputTakeoverParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_TAKEOVER_TEXT_LENGTH)
    lock_ms: int = Field(ge=1000, le=8000)
    type_ms_per_char: int = Field(ge=20, le=200)


class PhoneEchoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_ms: int = Field(ge=2000, le=10000)
    delay_ms: int = Field(ge=500, le=5000)


class InputTakeoverEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["input_takeover"]
    params: InputTakeoverParams


class PhoneEchoEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["phone_echo"]
    params: PhoneEchoParams


class _MetadataEffects(BaseModel):
    client_effect: InputTakeoverEffect | PhoneEchoEffect | None = Field(
        default=None, discriminator="kind"
    )
    authored_image_url: HttpUrl | None = None

    @field_validator("authored_image_url")
    @classmethod
    def _require_public_storage(cls, url: HttpUrl | None) -> HttpUrl | None:
        if url is not None and not _is_on_public_storage(str(url)):
            raise ValueError("authored_image_url must be on the public media storage")
        return url


def _public_storage_prefixes() -> list[str]:
    prefixes = [settings.core_api_public_url.rstrip("/") + LOCAL_UPLOADS_PATH]
    if settings.r2_public_base_url:
        prefixes.append(settings.r2_public_base_url.rstrip("/") + "/")
    return prefixes


def _is_on_public_storage(url: str) -> bool:
    """A player's browser loads this URL, so an arbitrary host would learn who
    played; only the storage this service writes to (R2, or the local uploads
    in development) is allowed."""
    return any(url.startswith(prefix) for prefix in _public_storage_prefixes())


def validate_condition_metadata(metadata: dict[str, object]) -> dict[str, object]:
    """Raises ValueError when an effect or image entry is malformed; other
    metadata keys (e.g. `placement`) pass through untouched."""
    effect_keys = (METADATA_CLIENT_EFFECT, METADATA_AUTHORED_IMAGE_URL)
    _MetadataEffects.model_validate(
        {key: metadata[key] for key in effect_keys if key in metadata}
    )
    return metadata
