import uuid

import pytest
from app.config import Settings
from app.exceptions.alpha_exceptions import (
    AlphaFeatureDisabledError,
    AlphaScenarioOnlyError,
)


def test_alpha_settings_default_to_off():
    settings = Settings(_env_file=None)

    assert settings.is_alpha_mode is False
    assert settings.alpha_scenario_id is None
    assert settings.is_turns_suspended is False


def test_alpha_mode_without_scenario_id_refuses_to_boot():
    with pytest.raises(ValueError, match="FATAL"):
        Settings(_env_file=None, is_alpha_mode=True, alpha_scenario_id=None)


def test_alpha_mode_with_scenario_id_boots():
    scenario_id = uuid.uuid4()

    settings = Settings(
        _env_file=None, is_alpha_mode=True, alpha_scenario_id=scenario_id
    )

    assert settings.alpha_scenario_id == scenario_id


def test_alpha_errors_are_403_with_a_stable_code():
    assert AlphaFeatureDisabledError().status_code == 403
    assert AlphaFeatureDisabledError().error_code == "alpha_feature_disabled"
    assert AlphaScenarioOnlyError().status_code == 403
    assert AlphaScenarioOnlyError().error_code == "alpha_scenario_only"
