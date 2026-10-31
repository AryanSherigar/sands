import pytest
from builders import make_negotiation_package
from pydantic import ValidationError
from strategy_contracts.scene import AcceptanceRange, ScenePackage
from strategy_contracts.scene_exchange import SceneAction, SceneDecision


def test_negotiation_package_round_trips() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())
    restored = ScenePackage.model_validate_json(package.model_dump_json())
    assert restored == package


def test_acceptance_range_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        AcceptanceRange(accept_at=1, haggle_at=5)


def test_extra_key_in_package_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ScenePackage.model_validate(make_negotiation_package(secret_limit=1))


def test_package_with_grudges_round_trips() -> None:
    raw = make_negotiation_package(
        hidden_limits={
            "grudges": [
                {
                    "id": "g1",
                    "text": "You broke the truce.",
                    "source": "opinion",
                    "band": "firm",
                    "is_inherited": True,
                    "predecessor_name": "King Aldric",
                }
            ]
        }
    )
    package = ScenePackage.model_validate(raw)
    assert package.hidden_limits is not None
    assert package.hidden_limits.grudges[0].predecessor_name == "King Aldric"


def test_more_cited_grudges_than_the_cap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SceneDecision(
            action=SceneAction.CONTINUE_TALK, cited_grudge_ids=["a", "b", "c", "d"]
        )


def test_a_package_stored_with_plain_grievances_is_upgraded_to_grudges() -> None:
    raw = make_negotiation_package(
        hidden_limits={"real_grievances": ["border raids", "a broken truce"]}
    )

    package = ScenePackage.model_validate(raw)

    assert package.hidden_limits is not None
    assert [(item.id, item.text) for item in package.hidden_limits.grudges] == [
        ("g1", "border raids"),
        ("g2", "a broken truce"),
    ]
    assert "real_grievances" not in package.model_dump_json()
