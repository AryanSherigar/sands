"""Unit tests for deterministic NPC voice assignment."""

import os
import subprocess
import sys

from app.turn.speaker_voice_pool import NPC_VOICE_POOL, resolve_npc_voice


def test_resolve_npc_voice_is_deterministic_within_a_process() -> None:
    assert resolve_npc_voice("Grimjaw") == resolve_npc_voice("Grimjaw")


def test_resolve_npc_voice_normalizes_case_and_whitespace() -> None:
    assert resolve_npc_voice("Grimjaw") == resolve_npc_voice("  grimjaw  ")


def test_resolve_npc_voice_returns_a_pool_member() -> None:
    assert resolve_npc_voice("Grimjaw") in NPC_VOICE_POOL


def test_resolve_npc_voice_different_names_can_differ() -> None:
    voices = {resolve_npc_voice(name) for name in ["Grimjaw", "Elowen", "Thessaly"]}
    assert len(voices) >= 2


def test_resolve_npc_voice_stable_across_python_hash_seeds() -> None:
    """Guards against a future regression to Python's built-in hash(), whose
    string hashing is randomized per process (PYTHONHASHSEED) unless
    disabled -- that would silently break "same NPC always gets the same
    voice" across restarts and replicas."""
    script = (
        "from app.turn.speaker_voice_pool import resolve_npc_voice;"
        "print(resolve_npc_voice('Grimjaw'))"
    )
    results = {
        subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for seed in ("1", "2", "3")
    }
    assert len(results) == 1
