"""Catalogue of the built-in premade animated avatars.

A fixed constant rather than a DB table, like default_music.py: the set is tiny
and changes only with a reseed (scripts/seed_premade_avatars.py), never at runtime.
"""

from dataclasses import dataclass

from app.integrations import storage_client
from app.models.premade_avatar import PremadeAvatar

PREMADE_OBJECT_PREFIX = "premade-avatars"
AVATAR_EXTENSION = ".mavatar"
PREVIEW_EXTENSION = ".webp"

MIKO_CREDIT = "Miko © Yuki Shindo (AITuber OnAir)"


@dataclass(frozen=True)
class PremadeAvatarEntry:
    slug: str
    name: str
    style: str
    credit: str | None = None


PREMADE_AVATARS: tuple[PremadeAvatarEntry, ...] = (
    PremadeAvatarEntry("mira", "Mira", "Anime", MIKO_CREDIT),
    PremadeAvatarEntry("hana", "Hana", "Anime"),
    PremadeAvatarEntry("aldric", "King Aldric", "Medieval"),
    PremadeAvatarEntry("isolde", "Queen Isolde", "Medieval"),
)


def avatar_object_key(entry: PremadeAvatarEntry) -> str:
    return f"{PREMADE_OBJECT_PREFIX}/{entry.slug}{AVATAR_EXTENSION}"


def preview_object_key(entry: PremadeAvatarEntry) -> str:
    return f"{PREMADE_OBJECT_PREFIX}/{entry.slug}{PREVIEW_EXTENSION}"


def premade_avatar_object_keys() -> frozenset[str]:
    return frozenset(avatar_object_key(entry) for entry in PREMADE_AVATARS)


def list_premade_avatars() -> list[PremadeAvatar]:
    return [
        PremadeAvatar(
            id=entry.slug,
            name=entry.name,
            style=entry.style,
            avatar_url=storage_client.public_url_for(avatar_object_key(entry)),
            preview_url=storage_client.public_url_for(preview_object_key(entry)),
            credit=entry.credit,
        )
        for entry in PREMADE_AVATARS
    ]
