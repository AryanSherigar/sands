"""Count every event kind in AI-only headless games: python scripts/feature_census.py <scenario.json> --turns 120 --seeds 1 2 3."""

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.ai import headless
from app.models.world_player import PlayerRuler
from strategy_contracts.scenario import StrategyScenario
from war_metrics import (
    WarLedger,
    summarize_map,
    summarize_stability,
    summarize_wars,
)

RULER = PlayerRuler(
    name="Observer",
    trait_ids=["honorable", "cautious"],
    ambition_ids=["ambition_peace"],
)
WATCHED_PREFIXES = (
    "alliance",
    "coalition",
    "vassal",
    "treaty",
    "trade",
    "tribute",
    "war_declared",
    "peace_signed",
    "ruler_",
    "uprising",
    "prisoner",
    "hostage",
    "mediation",
)


def load_scenario(path: str) -> StrategyScenario:
    with open(path) as handle:
        return StrategyScenario.model_validate(json.load(handle))


def apply_tuning_overrides(scenario: StrategyScenario, pairs: list[str]) -> None:
    for pair in pairs:
        path, value = pair.split("=")
        section, field = path.split(".")
        current = getattr(scenario.tuning, section)
        setattr(
            scenario.tuning, section, current.model_copy(update={field: int(value)})
        )


def play_and_count(scenario: StrategyScenario, seed: int, turns: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    ledger = WarLedger()
    original = headless._play_turn

    def counting_play(world, scenario_in):
        result = original(world, scenario_in)
        counts.update(event.kind for event in result.events)
        ledger.observe(result.world, result.events)
        return result

    headless._play_turn = counting_play
    try:
        report = headless.run_headless(scenario, seed, turns, RULER)
    finally:
        headless._play_turn = original
    print(
        f"seed {seed}: {report.turns_run} turns, flags: {', '.join(report.flags) or 'none'}"
    )
    for line in (
        summarize_wars(ledger),
        summarize_stability(report),
        summarize_map(report),
    ):
        print(line)
    return counts


def print_watched(counts: Counter[str]) -> None:
    watched = {
        kind: count
        for kind, count in sorted(counts.items())
        if kind.startswith(WATCHED_PREFIXES)
    }
    print(f"  {watched}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario")
    parser.add_argument("--turns", type=int, default=120)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1])
    parser.add_argument("--tuning", nargs="*", default=[], metavar="SECTION.FIELD=INT")
    arguments = parser.parse_args()
    scenario = load_scenario(arguments.scenario)
    apply_tuning_overrides(scenario, arguments.tuning)
    for seed in arguments.seeds:
        print_watched(play_and_count(scenario, seed, arguments.turns))


if __name__ == "__main__":
    main()
