from typing import ClassVar

import pytest
from app.services.strategy_playthrough import derive_ruler
from pydantic import ValidationError
from strategy_contracts.scenario import PlayerRulerCustomization


def _customization(**overrides: object) -> PlayerRulerCustomization:
    fields: dict[str, object] = {
        "name": "Aldric",
        "trait_ids": ["brave", "wise"],
        "ambition_ids": ["conquest"],
    }
    fields.update(overrides)
    return PlayerRulerCustomization(**fields)


class _DocumentStub:
    factions: ClassVar[list[object]] = []


def test_derive_ruler_keeps_chosen_chronicler() -> None:
    ruler = derive_ruler(
        _DocumentStub(),  # type: ignore[arg-type]
        "any",
        _customization(chronicler_id="vaelen"),
    )
    assert ruler.chronicler_id == "vaelen"


def test_derive_ruler_defaults_to_lucan() -> None:
    ruler = derive_ruler(
        _DocumentStub(),  # type: ignore[arg-type]
        "any",
        _customization(),
    )
    assert ruler.chronicler_id == "lucan"


def test_unknown_chronicler_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _customization(chronicler_id="nobody")
