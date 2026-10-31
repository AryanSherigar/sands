import pytest
from builders import make_negotiation_package
from pydantic import ValidationError
from strategy_contracts.scene import PublicScenePackage, ScenePackage


def test_public_scene_omits_private_limits() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())

    public = PublicScenePackage.model_validate(
        package.model_dump(exclude={"hidden_limits"})
    )

    assert "hidden_limits" not in public.model_dump()


def test_public_scene_rejects_private_limits() -> None:
    with pytest.raises(ValidationError):
        PublicScenePackage.model_validate(make_negotiation_package())
