import os

import pytest
from app.config import settings
from app.integrations import openai_compatible_client

from .budget_loader import LEDGER_PATH
from .budget_loader import live_budget as live_budget_module

ENV_MUSE_KEY = "MUSE_API_KEY"
ENV_RUN_LABEL = "LIVE_RUN_LABEL"
DEFAULT_RUN_LABEL = "trs-scenes"


def pytest_collection_modifyitems(config, items):
    if os.environ.get(ENV_MUSE_KEY):
        return
    skip = pytest.mark.skip(reason=f"{ENV_MUSE_KEY} is not set")
    for item in items:
        if item.get_closest_marker("live_scene") is not None:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def live_models():
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(settings, "openai_compatible_api_key", os.environ[ENV_MUSE_KEY])
        patcher.setattr(openai_compatible_client, "_client", None)
        yield
        patcher.setattr(openai_compatible_client, "_client", None)


@pytest.fixture(scope="session")
def live_budget(live_models):
    budget = live_budget_module.LiveBudget.from_env(LEDGER_PATH)
    try:
        budget.check_can_start()
    except live_budget_module.LiveBudgetExhausted:
        pytest.skip("the live token budget is spent")
    yield budget
    if budget.used_input > 0:
        budget.record_run(os.environ.get(ENV_RUN_LABEL, DEFAULT_RUN_LABEL))
