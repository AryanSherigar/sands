"""Keeps the frontend's hand-written constant files in step with Core API.

The frontend owns display text; Core API owns the keys and the `requires`
edges. This test parses the TypeScript constant files with regexes (they are
written to stay regex-friendly) and fails when the two sides disagree.
"""

import re
from pathlib import Path

from app.models.condition import SENSORY_CUE_IDS
from app.tools.registry import TOOLS

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
SCENARIO_TOOLS_TS = FRONTEND_SRC / "shared" / "constants" / "scenario-tools.ts"

TOOL_BLOCK = re.compile(
    r'key:\s*"(?P<key>\w+)"[^}]*?requires:\s*\[(?P<requires>[^\]]*)\]', re.S
)


def _frontend_tools() -> dict[str, tuple[str, ...]]:
    source = SCENARIO_TOOLS_TS.read_text()
    parsed: dict[str, tuple[str, ...]] = {}
    for match in TOOL_BLOCK.finditer(source):
        requires = tuple(re.findall(r'"(\w+)"', match.group("requires")))
        parsed[match.group("key")] = requires
    return parsed


def test_frontend_tool_keys_match_core_api_registry_in_order() -> None:
    assert list(_frontend_tools()) == list(TOOLS)


def test_frontend_requires_edges_match_core_api_registry() -> None:
    expected = {key: definition.requires for key, definition in TOOLS.items()}

    assert _frontend_tools() == expected


def test_frontend_tool_keys_tuple_matches_core_api_registry() -> None:
    source = SCENARIO_TOOLS_TS.read_text()
    tuple_body = re.search(r"TOOL_KEYS\s*=\s*\[(?P<body>[^\]]*)\]", source, re.S)

    assert tuple_body is not None
    assert tuple(re.findall(r'"(\w+)"', tuple_body.group("body"))) == tuple(TOOLS)


SENSORY_CUES_TS = FRONTEND_SRC / "shared" / "constants" / "sensory-cues.ts"


def test_frontend_sensory_cue_ids_match_core_api_in_order() -> None:
    source = SENSORY_CUES_TS.read_text()
    body = re.search(r"SENSORY_CUE_IDS\s*=\s*\[(?P<body>[^\]]*)\]", source, re.S)

    assert body is not None
    assert tuple(re.findall(r'"(\w+)"', body.group("body"))) == SENSORY_CUE_IDS


CHECK_TYPES_TS = FRONTEND_SRC / "shared" / "types" / "check.types.ts"


def test_frontend_rule_check_kinds_match_core_api_in_order() -> None:
    from app.models.rule_check import RULE_CHECK_KINDS

    source = CHECK_TYPES_TS.read_text()
    body = re.search(r"RULE_CHECK_KINDS[^=]*=\s*\[(?P<body>[^\]]*)\]", source, re.S)

    assert body is not None
    assert tuple(re.findall(r'"(\w+)"', body.group("body"))) == RULE_CHECK_KINDS


MINIGAME_TYPES_TS = FRONTEND_SRC / "shared" / "types" / "minigame.types.ts"


def test_frontend_minigame_types_match_core_api_in_order() -> None:
    from app.models.minigame import MINIGAME_TYPES

    source = MINIGAME_TYPES_TS.read_text()
    body = re.search(r"MINIGAME_TYPES\s*=\s*\[(?P<body>[^\]]*)\]", source, re.S)

    assert body is not None
    assert tuple(re.findall(r'"(\w+)"', body.group("body"))) == MINIGAME_TYPES


DISPLAY_HINTS_TS = FRONTEND_SRC / "shared" / "constants" / "display-hints.ts"


def _ts_tuple(source: str, name: str) -> tuple[str, ...]:
    body = re.search(rf"{name}\s*(?::[^=]+)?=\s*\[(?P<body>[^\]]*)\]", source, re.S)
    assert body is not None, name
    return tuple(re.findall(r'"(\w+)"', body.group("body")))


def test_frontend_display_hint_kinds_and_clock_formats_match_core_api() -> None:
    from app.services.display_hints import CLOCK_FORMATS, HINT_KINDS

    source = DISPLAY_HINTS_TS.read_text()

    assert _ts_tuple(source, "DISPLAY_HINT_KINDS") == HINT_KINDS
    assert _ts_tuple(source, "CLOCK_FORMATS") == CLOCK_FORMATS


RULE_SHEET_TYPES_TS = FRONTEND_SRC / "shared" / "types" / "rule-sheet.types.ts"
SHEET_RULE_CONSTANTS_TS = (
    FRONTEND_SRC / "features" / "studio" / "constants" / "sheetRule.ts"
)


def test_frontend_rule_sheet_hands_and_statuses_match_core_api() -> None:
    from app.models.sheet_rule import INITIAL_STATUSES, RULE_STATUSES, SOURCE_STYLES

    source = RULE_SHEET_TYPES_TS.read_text()

    assert _ts_tuple(source, "RULE_HANDS") == SOURCE_STYLES
    shown = tuple(status for status in RULE_STATUSES if status != "unrevealed")
    assert _ts_tuple(source, "RULE_STATUSES") == shown
    assert _ts_tuple(SHEET_RULE_CONSTANTS_TS.read_text(), "INITIAL_STATUSES") == (
        INITIAL_STATUSES
    )


AUDIO_CONSTANTS_TS = FRONTEND_SRC / "shared" / "constants" / "audio.ts"


def test_frontend_mood_list_matches_core_api_mood_slots() -> None:
    from app.db.models.scenario_music import MOOD_SLOTS

    assert _ts_tuple(AUDIO_CONSTANTS_TS.read_text(), "SCENARIO_MOODS") == MOOD_SLOTS
