from pathlib import Path

import pytest
from scripts.reincarnated_aristocrat import map_assets, maps
from scripts.reincarnated_aristocrat.builder import build
from scripts.reincarnated_aristocrat.mapart.constants import MAP_ASSET_DIR
from scripts.reincarnated_aristocrat.mapart.naming import map_file_name
from scripts.reincarnated_aristocrat.mapart.render import render_all


def _file_names() -> list[str]:
    return [map_file_name(seed) for seed in maps.map_seeds(with_images=False)]


def test_map_seeds_carry_urls_unless_images_are_off() -> None:
    assert all(seed.image_url for seed in maps.map_seeds())
    assert all(seed.image_url is None for seed in maps.map_seeds(with_images=False))
    assert [seed.display_order for seed in maps.map_seeds()] == list(range(8))


def test_every_image_url_points_at_the_map_prefix() -> None:
    for seed in maps.map_seeds():
        assert map_assets.MAP_OBJECT_PREFIX in str(seed.image_url)
        assert str(seed.image_url).endswith(map_file_name(seed))


def test_build_without_map_images_keeps_the_layouts() -> None:
    built = build(with_map_images=False)
    assert len(built.maps) == 8
    assert all(seed.image_url is None for seed in built.maps)


def test_committed_images_exist_for_every_map() -> None:
    for name in _file_names():
        assert (MAP_ASSET_DIR / name).is_file(), name


async def test_upload_sends_every_file_under_its_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    render_all(maps.map_seeds(with_images=False), tmp_path)
    sent: dict[str, str] = {}

    async def fake_upload(content: bytes, content_type: str, object_key: str) -> str:
        assert content.startswith(b"\x89PNG")
        sent[object_key] = content_type
        return object_key

    monkeypatch.setattr(map_assets.storage_client, "upload_image", fake_upload)
    await map_assets.upload_map_images(_file_names(), tmp_path)
    assert len(sent) == 8
    assert set(sent.values()) == {"image/png"}
    assert all(key.startswith(map_assets.MAP_OBJECT_PREFIX) for key in sent)


async def test_upload_fails_loudly_when_an_image_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await map_assets.upload_map_images(_file_names(), tmp_path)
