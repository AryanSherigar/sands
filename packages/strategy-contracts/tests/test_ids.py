import pytest
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.ids import EntityId

ENTITY_ID_ADAPTER = TypeAdapter(EntityId)


def test_valid_slug_is_accepted() -> None:
    assert ENTITY_ID_ADAPTER.validate_python("region_ashford") == "region_ashford"


@pytest.mark.parametrize("bad_id", ["Region", "a", "", "has space", "x" * 41, "9lives"])
def test_invalid_slug_is_rejected(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        ENTITY_ID_ADAPTER.validate_python(bad_id)
