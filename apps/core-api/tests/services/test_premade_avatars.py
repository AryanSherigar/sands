from pathlib import Path

import pytest
from app.exceptions.entity_exceptions import EntityValidationError
from app.services import premade_avatars
from app.services.entity_service import EntityService

PREMADE_DIR = Path(__file__).resolve().parents[4] / "premade-avatars"


def test_every_catalogue_entry_has_its_asset_files_in_the_repo():
    for entry in premade_avatars.PREMADE_AVATARS:
        assert (PREMADE_DIR / f"{entry.slug}.mavatar").is_file()
        assert (PREMADE_DIR / f"{entry.slug}.webp").is_file()


def test_list_premade_avatars_builds_urls_from_object_keys():
    listed = premade_avatars.list_premade_avatars()
    assert len(listed) == len(premade_avatars.PREMADE_AVATARS)
    assert listed[1].avatar_url.endswith("/premade-avatars/mei.mavatar")
    assert listed[1].preview_url.endswith("/premade-avatars/mei.webp")
    assert listed[2].avatar_url.endswith("/premade-avatars/eleanor.mavatar")
    assert listed[2].name == "Queen Eleanor"


def test_character_validation_accepts_a_premade_avatar_url():
    premade = premade_avatars.list_premade_avatars()[1]
    EntityService._validate_character_avatar("character", premade.avatar_url)


def test_character_validation_still_rejects_other_urls():
    with pytest.raises(EntityValidationError):
        EntityService._validate_character_avatar(
            "character", "http://localhost:8000/uploads/premade-avatars/other.mavatar"
        )
