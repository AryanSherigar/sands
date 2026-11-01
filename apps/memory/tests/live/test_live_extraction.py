"""Gated live smoke against the real Meta Muse extraction endpoint (spends money).

Run: pytest -m live_extraction -s tests/live/test_live_extraction.py
Skipped when MUSE_API_KEY is in neither the repo-root .env nor the process env.
"""

import os
from pathlib import Path

import pytest
from app.integrations.muse_extraction_client import MuseExtractionClient
from app.services.extraction_input import load_system_prompt, render_user_content

API_KEY_NAME = "MUSE_API_KEY"
LIVE_ENV_FILE_VARIABLE = "LIVE_ENV_FILE"
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
LIVE_MODEL_NAME = "muse-spark-1.3"
LIVE_BASE_URL = "https://api.meta.ai/v1"
LIVE_MAX_TOKENS = 8192
CLIENT_TIMEOUT_SECONDS = 150
VALE_ID = "22222222-2222-2222-2222-222222222222"
PLAYER_ID = "33333333-3333-3333-3333-333333333333"
TURNS = (
    "### Turn 1 (actor: Mira)\n"
    "S1.1 [action] I tell Captain Vale I will guard the ferry at dawn.\n"
    "S1.2 [narration] Vale nods. Mira swears on her blade to guard the ferry at dawn, "
    "and Old Marta, the ferrywoman, hands her the lantern.\n"
)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _separator, raw_value = stripped.partition("=")
        values[name.strip()] = raw_value.strip().strip("'\"")
    return values


def _resolve_api_key() -> str:
    env_file = Path(os.environ.get(LIVE_ENV_FILE_VARIABLE) or REPO_ROOT_ENV_FILE)
    from_file = _parse_env_file(env_file).get(API_KEY_NAME, "")
    return from_file or os.environ.get(API_KEY_NAME, "")


API_KEY = _resolve_api_key()
if not API_KEY:
    pytest.skip(f"{API_KEY_NAME} not available", allow_module_level=True)

pytestmark = pytest.mark.live_extraction


def _user_content() -> str:
    return render_user_content(
        turns=TURNS,
        context="(none)",
        roster=(
            f"{VALE_ID} | character | Captain Vale\n"
            f"{PLAYER_ID} | character | The Wanderer | player character"
        ),
        tracked="(none)",
        scene="(none)",
    )


def _client(reasoning_effort: str) -> MuseExtractionClient:
    return MuseExtractionClient(
        api_key=API_KEY,
        base_url=LIVE_BASE_URL,
        model_name=LIVE_MODEL_NAME,
        timeout_seconds=CLIENT_TIMEOUT_SECONDS,
        max_tokens=LIVE_MAX_TOKENS,
        reasoning_effort=reasoning_effort,
    )


async def test_minimal_reasoning_returns_parseable_output() -> None:
    result = await _client("minimal").extract(load_system_prompt(), _user_content())

    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0
    assert set(result.raw_output) == {
        "new_entities",
        "facts",
        "supersessions",
        "new_commitments",
        "commitment_updates",
        "scene",
    }
    print("live extraction output:", result.raw_output)
