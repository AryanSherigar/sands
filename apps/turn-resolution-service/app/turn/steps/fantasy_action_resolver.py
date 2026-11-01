"""Build a whole candidate state for an authored fantasy action."""

from dataclasses import dataclass

from app.exceptions.fantasy_exceptions import FantasyActionError
from app.turn.fantasy_rules import resolve_fantasy_action


@dataclass(frozen=True)
class FantasyActionResolution:
    state: dict[str, object]
    mutated_paths: set[str]
    instruction: str


def resolve_action(
    action_id: str, state: dict[str, object], snapshot: dict[str, object]
) -> FantasyActionResolution:
    if snapshot.get("mode") != "master":
        raise FantasyActionError("Fantasy actions require an Advanced scenario.")
    config = snapshot.get("fantasy_mechanics")
    if not isinstance(config, dict):
        raise FantasyActionError("Fantasy mechanics are unavailable.")
    candidate = resolve_fantasy_action(state, config, action_id)
    if action_id == "rest":
        return FantasyActionResolution(
            candidate,
            {"player.coins", "player.energy"},
            "The player paid for a full rest. Narrate the completed rest.",
        )
    return FantasyActionResolution(
        candidate,
        {"player.coins", "quests.retrieval.stage"},
        "The player claimed the retrieval reward. Narrate the completed exchange.",
    )
