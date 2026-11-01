"""Deterministic NPC voice assignment for narration audio.

Uses hashlib.sha256, never Python's built-in hash() -- CPython randomizes
string hashes per process (PYTHONHASHSEED) unless explicitly disabled, which
would silently break the "same NPC name always gets the same voice"
guarantee across restarts and replicas.

NOTE: this roster must be verified against Gemini's current documented
prebuilt-voice list for settings.text_to_speech_model before relying on it
in production -- it was not possible to confirm the live voice catalog from
this environment.
"""

import hashlib

NPC_VOICE_POOL: tuple[str, ...] = (
    "Puck",
    "Charon",
    "Fenrir",
    "Aoede",
    "Orus",
    "Zephyr",
)


def resolve_npc_voice(npc_name: str, pool: tuple[str, ...] = NPC_VOICE_POOL) -> str:
    """Deterministically map an NPC name to one voice in pool."""
    digest = hashlib.sha256(npc_name.strip().lower().encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % len(pool)
    return pool[index]
