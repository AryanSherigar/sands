import re
from pathlib import Path

from app.turn.tools import KNOWN_TOOLS, enabled_tools, is_enabled

CORE_API_REGISTRY = (
    Path(__file__).resolve().parents[3] / "core-api" / "app" / "tools" / "registry.py"
)


def test_missing_enabled_tools_means_no_tools() -> None:
    assert enabled_tools({}) == []
    assert is_enabled({}, "rule_checks") is False


def test_old_snapshot_without_the_key_is_treated_as_empty() -> None:
    old_snapshot = {"mode": "master", "state_mutation": {"path": "a.b"}}

    assert enabled_tools(old_snapshot) == []


def test_is_enabled_reads_membership() -> None:
    snapshot = {"enabled_tools": ["rule_checks", "status_hud"]}

    assert is_enabled(snapshot, "status_hud") is True
    assert is_enabled(snapshot, "atmosphere") is False


def test_unknown_or_malformed_values_are_ignored() -> None:
    assert enabled_tools({"enabled_tools": "rule_checks"}) == []
    assert enabled_tools({"enabled_tools": ["rule_checks", 7, "teleporter"]}) == [
        "rule_checks"
    ]


def test_known_tools_equal_core_api_registry_keys() -> None:
    source = CORE_API_REGISTRY.read_text()
    registry_keys = set(re.findall(r'^    "(\w+)": ToolDefinition\(', source, re.M))

    assert registry_keys
    assert set(KNOWN_TOOLS) == registry_keys
