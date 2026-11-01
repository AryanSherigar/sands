import os

import pytest
from app.config import Settings

from tests.live.budget_loader import LEDGER_PATH
from tests.live.budget_loader import live_budget as live_budget_module

ENV_MUSE_KEY = "MUSE_API_KEY"
ENV_RUN_LABEL = "LIVE_RUN_LABEL"
DEFAULT_RUN_LABEL = "simulation-providers"
PROVIDER_URL = "https://api.meta.ai/v1/chat/completions"
PROVIDER_MODEL = "muse-spark-1.3"


def pytest_collection_modifyitems(config, items):
    if os.environ.get(ENV_MUSE_KEY):
        return
    skip = pytest.mark.skip(reason=f"{ENV_MUSE_KEY} is not set")
    for item in items:
        if item.get_closest_marker("live_provider") is not None:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    key = os.environ[ENV_MUSE_KEY]
    values: dict[str, object] = {
        "llm_provider_protocol": "chat_completions",
        "llm_provider_reasoning_effort": "minimal",
    }
    for name in ("intent", "speech", "stance"):
        values[f"{name}_provider_enabled"] = True
        values[f"{name}_provider_url"] = PROVIDER_URL
        values[f"{name}_provider_api_key"] = key
        values[f"{name}_provider_model"] = PROVIDER_MODEL
    return Settings(**values)


@pytest.fixture(scope="session")
def live_budget():
    budget = live_budget_module.LiveBudget.from_env(LEDGER_PATH)
    try:
        budget.check_can_start()
    except live_budget_module.LiveBudgetExhausted:
        pytest.skip("the live token budget is spent")
    yield budget
    if budget.used_input > 0:
        budget.record_run(os.environ.get(ENV_RUN_LABEL, DEFAULT_RUN_LABEL))
