"""Stable ids: every corpus key maps to the same UUID on every run."""

from uuid import NAMESPACE_URL, UUID, uuid5

CORPUS_NAMESPACE = uuid5(NAMESPACE_URL, "https://sands.example/memory-eval-corpus")
SCENARIO_KEY = "scenario"
PLAYTHROUGH_KEY = "playthrough"
DECOY_PLAYTHROUGH_KEY = "decoy_playthrough"


def key_uuid(campaign_id: str, key: str) -> UUID:
    return uuid5(CORPUS_NAMESPACE, f"{campaign_id}:{key}")


def turn_uuid(campaign_id: str, playthrough_key: str, turn_number: int) -> UUID:
    return key_uuid(campaign_id, f"{playthrough_key}:turn:{turn_number}")
