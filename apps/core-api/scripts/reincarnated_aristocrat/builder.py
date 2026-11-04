"""Assembles the appraisal scenario in the order the evaluator must see it."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.condition import ConditionCreate
from app.models.end_condition import EndConditionCreate
from app.models.fact import FactCreate
from app.models.invariant import InvariantCreate
from app.models.minigame import MinigameCreate
from app.models.rule_check import RuleCheckCreate
from app.models.sheet_rule import SheetRuleCreate
from scripts.reincarnated_aristocrat import maps, prose, schema
from scripts.reincarnated_aristocrat.characters import character_seeds
from scripts.reincarnated_aristocrat.conditions.appraisal import appraisal_conditions
from scripts.reincarnated_aristocrat.conditions.beats import beat_conditions
from scripts.reincarnated_aristocrat.conditions.betrayal import betrayal_conditions
from scripts.reincarnated_aristocrat.conditions.clock import clock_conditions
from scripts.reincarnated_aristocrat.conditions.monthly import monthly_conditions
from scripts.reincarnated_aristocrat.conditions.policies import policy_conditions
from scripts.reincarnated_aristocrat.conditions.recruit import recruit_conditions
from scripts.reincarnated_aristocrat.conditions.training import training_conditions
from scripts.reincarnated_aristocrat.endings import end_conditions
from scripts.reincarnated_aristocrat.locations import location_seeds
from scripts.seeding.expr import Cond, to_condition
from scripts.seeding.types import EntitySeed, MapSeed

ACTION_CHIPS = [
    "Appraise someone",
    "Look around",
    "Train a retainer",
    "Review the House",
]
ENABLED_TOOLS = ["status_hud"]


@dataclass(frozen=True)
class AppraisalScenario:
    scenario: dict[str, object]
    entities: Sequence[EntitySeed]
    facts: Sequence[FactCreate]
    conditions: Sequence[ConditionCreate]
    end_conditions: Sequence[EndConditionCreate]
    invariants: Sequence[InvariantCreate]
    minigames: Sequence[MinigameCreate]
    rule_checks: Sequence[RuleCheckCreate]
    sheet_rules: Sequence[SheetRuleCreate]
    maps: Sequence[MapSeed]


def scenario_columns() -> dict[str, object]:
    return {
        "title": prose.TITLE,
        "logline": prose.LOGLINE,
        "mode": "master",
        "visibility": "private",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["isekai", "fantasy", "strategy"],
        "content_tag": "teen",
        "content_tags": ["political-intrigue", "found-family", "moral-ambiguity"],
        "is_mature": False,
        "estimated_playtime": prose.PLAYTIME,
        "narrator_persona": prose.PERSONA,
        "opening_scene": prose.OPENING_SCENE,
        "world_data": {
            "openingPrompt": prose.OPENING_SCENE,
            "fallback_narration": prose.FALLBACK_NARRATION,
        },
        "setup_schema": [],
        "state_schema": schema.build_state_schema(),
        "checkpoints": [],
        "rules": {
            "narration_max_output_tokens": prose.NARRATION_MAX_OUTPUT_TOKENS,
            "intent_marker_group": schema.INTENT_GROUP,
        },
        "action_chips": ACTION_CHIPS,
        "enabled_tools": list(ENABLED_TOOLS),
    }


def ordered_conditions() -> list[Cond]:
    return [
        *clock_conditions(),
        *beat_conditions(),
        *appraisal_conditions(),
        *recruit_conditions(),
        *training_conditions(),
        *policy_conditions(),
        *monthly_conditions(),
        *betrayal_conditions(),
    ]


def build(with_map_images: bool = True) -> AppraisalScenario:
    return AppraisalScenario(
        scenario=scenario_columns(),
        entities=[*character_seeds(), *location_seeds()],
        facts=[],
        conditions=[to_condition(cond) for cond in ordered_conditions()],
        end_conditions=end_conditions(),
        invariants=[],
        minigames=[],
        rule_checks=[],
        sheet_rules=[],
        maps=maps.map_seeds(with_map_images),
    )
