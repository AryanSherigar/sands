import pytest
from app.models.sheet_rule import SheetRuleCreate, SheetRuleUpdate
from pydantic import ValidationError


def _create(**overrides) -> SheetRuleCreate:
    base = {"key": "r3", "number": 3, "text": "Answer the phone only once."}
    base.update(overrides)
    return SheetRuleCreate(**base)


def test_defaults_are_an_intact_typed_unflagged_rule() -> None:
    rule = _create()

    assert rule.initial_status == "intact"
    assert rule.source_style == "typed"
    assert rule.is_ai_flaggable is False
    assert rule.corrupted_text is None


@pytest.mark.parametrize("key", ["R3", "3r", "has space", "", "x" * 32, "a-b"])
def test_bad_keys_are_rejected(key: str) -> None:
    with pytest.raises(ValidationError):
        _create(key=key)


@pytest.mark.parametrize("number", [0, 100, -1])
def test_number_must_be_between_1_and_99(number: int) -> None:
    with pytest.raises(ValidationError):
        _create(number=number)


def test_text_is_required_and_bounded() -> None:
    with pytest.raises(ValidationError):
        _create(text="")
    with pytest.raises(ValidationError):
        _create(text="x" * 601)
    with pytest.raises(ValidationError):
        _create(corrupted_text="x" * 601)


@pytest.mark.parametrize("status", ["active_threat", "violated", "corrupted", "x"])
def test_initial_status_is_unrevealed_or_intact_only(status: str) -> None:
    with pytest.raises(ValidationError):
        _create(initial_status=status)


def test_unknown_source_style_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(source_style="crayon")


def test_update_cannot_rename_the_key() -> None:
    update = SheetRuleUpdate(**{"key": "other", "text": "New wording."})

    assert not hasattr(update, "key")
    assert update.model_dump(exclude_unset=True) == {"text": "New wording."}


def test_update_can_explicitly_clear_corrupted_text() -> None:
    update = SheetRuleUpdate(corrupted_text=None)

    assert update.model_dump(exclude_unset=True) == {"corrupted_text": None}
