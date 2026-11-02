"""Headless AI-vs-AI balance run: python scripts/ai_balance_run.py --turns 120 --seeds 1 2 3."""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.ai.headless import OBSERVER_FACTION_ID, HeadlessReport, run_headless
from app.models.world_player import PlayerRuler
from strategy_contracts.examples import load_three_crowns_expanded

DEFAULT_TURNS = 120
DEFAULT_SEEDS = (1, 2, 3)
RULER = PlayerRuler(
    name="Observer",
    trait_ids=["honorable", "cautious"],
    ambition_ids=["ambition_peace"],
)


def format_report(report: HeadlessReport) -> str:
    last = report.samples[-1]
    treasuries = {
        faction_id: gold
        for faction_id, gold in last.treasury_by_faction.items()
        if faction_id != OBSERVER_FACTION_ID
    }
    flags = ", ".join(report.flags) or "none"
    return (
        f"seed {report.seed}: {report.turns_run} turns, flags: {flags}\n"
        f"  regions {last.regions_by_owner}\n"
        f"  treasury {treasuries}\n"
        f"  wars {last.war_count}, orders planned "
        f"{sum(sample.planned_orders for sample in report.samples)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turns", type=int, default=DEFAULT_TURNS)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    arguments = parser.parse_args()
    scenario = load_three_crowns_expanded()
    for seed in arguments.seeds:
        print(format_report(run_headless(scenario, seed, arguments.turns, RULER)))


if __name__ == "__main__":
    main()
