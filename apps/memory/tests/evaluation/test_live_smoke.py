"""Gated: starts a scratch memory service and a scratch database, calls real models.

Run: pytest -m live_eval -s tests/evaluation/test_live_smoke.py
"""

import pytest
from app.config import get_settings
from eval.credentials import MissingCredentialsError, resolve_api_key
from eval.driver import UsageTotals
from eval.memory_http import MemoryHttp
from eval.runner import RunEnv, run_campaign
from eval.stack import (
    MEMORY_ROOT,
    QUALITY_EMBED_TIMEOUT_SECONDS,
    start_stack,
    stop_stack,
)
from tests.evaluation.campaign_helpers import make_smoke_campaign

pytestmark = pytest.mark.live_eval
SMOKE_RUN_NAME = "smoke"


async def test_planted_span_is_recalled_and_decoy_marker_never_leaks() -> None:
    settings = get_settings()
    try:
        api_key = resolve_api_key(settings)
    except MissingCredentialsError:
        pytest.skip("GOOGLE_CLOUD_API_KEY not available")
    stack = await start_stack(
        settings.memory_database_url,
        SMOKE_RUN_NAME,
        api_key,
        QUALITY_EMBED_TIMEOUT_SECONDS,
        MEMORY_ROOT / "eval" / "reports" / "smoke.service.log",
    )
    http = MemoryHttp(stack.base_url)
    env = RunEnv(
        http, stack.database_url, lambda _: None, settings.embedding_model_name, False
    )
    try:
        outcome = await run_campaign(env, make_smoke_campaign())
    finally:
        await http.close()
        await stop_stack(stack, settings.memory_database_url, True)
    by_arm = {(r.arm, r.probe_id): r for r in outcome.probes}
    assert by_arm[("memory", "smoke_long")].required_found == 1
    assert by_arm[("baseline", "smoke_long")].required_found == 0
    assert by_arm[("memory", "smoke_iso")].forbidden_count == 0
    assert isinstance(env.usage, UsageTotals)
