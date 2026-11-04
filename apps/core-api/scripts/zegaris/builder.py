"""Assembles the Zegaris scenario in the order the evaluator must see it."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.condition import ConditionCreate
from app.models.end_condition import EndConditionCreate
from app.models.fact import FactCreate
from app.models.invariant import InvariantCreate
from app.models.minigame import MinigameCreate
from app.models.rule_check import RuleCheckCreate
from app.models.sheet_rule import SheetRuleCreate
from scripts.seeding.expr import Cond, to_condition
from scripts.seeding.types import EntitySeed, MapSeed
from scripts.zegaris import maps, prose, schema
from scripts.zegaris.combat import fantasy_combat
from scripts.zegaris.conditions.access import access_conditions
from scripts.zegaris.conditions.retrieval import retrieval_conditions
from scripts.zegaris.conditions.tithe import tithe_conditions
from scripts.zegaris.entities import entity_seeds
from scripts.zegaris.map_assets import cover_image_url, has_cover_image
from scripts.zegaris.mechanics import CLASS_LOADOUTS, fantasy_mechanics

ACTION_CHIPS = [
    "Ask Veya about work",
    "Look around the room",
    "Take the east road",
    "Take the west road",
]
CLASS_LABELS = {
    "disgraced_knight": "The Disgraced Knight",
    "rogue_apprentice": "The Rogue Apprentice",
    "fugitive_smuggler": "The Fugitive Smuggler",
    "last_priest": "The Last Priest",
}
CLASS_FIELD = "outlander_class"
NAME_FIELD = {
    "id": "character_name",
    "key": "character_name",
    "label": "Your name",
    "type": "text",
    "required": True,
    "options": [],
    "is_character_name": True,
}


@dataclass(frozen=True)
class ZegarisScenario:
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


def setup_schema() -> list[dict[str, object]]:
    background = {
        "id": CLASS_FIELD,
        "key": CLASS_FIELD,
        "label": "Your background",
        "type": "single_select",
        "required": True,
        "options": [
            {"id": key, "value": key, "label": CLASS_LABELS[key]}
            for key in CLASS_LOADOUTS
        ],
    }
    return [NAME_FIELD, background]


def scenario_columns() -> dict[str, object]:
    return {
        "title": prose.TITLE,
        "cover_image_url": cover_image_url() if has_cover_image() else None,
        "logline": prose.LOGLINE,
        "mode": "master",
        "visibility": "private",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["High Fantasy", "Cosmic Horror"],
        "content_tag": "mature",
        "content_tags": ["horror-themes", "moral-ambiguity", "heavy-themes"],
        "is_mature": True,
        "estimated_playtime": prose.PLAYTIME,
        "narrator_persona": prose.PERSONA,
        "opening_scene": prose.OPENING_SCENE,
        "world_data": {
            "openingPrompt": prose.OPENING_SCENE,
            "fallback_narration": prose.FALLBACK_NARRATION,
        },
        "setup_schema": setup_schema(),
        "state_schema": schema.build_state_schema(),
        "checkpoints": [],
        "rules": {
            "narration_max_output_tokens": prose.NARRATION_MAX_OUTPUT_TOKENS,
            "intent_marker_group": schema.INTENT_GROUP,
            "fantasy_mechanics": fantasy_mechanics(),
            "fantasy_combat": fantasy_combat(),
        },
        "action_chips": ACTION_CHIPS,
        "enabled_tools": [],
    }


def ordered_conditions() -> list[Cond]:
    return [
        *tithe_conditions(),
        *access_conditions(),
        *retrieval_conditions(),
    ]


def build() -> ZegarisScenario:
    return ZegarisScenario(
        scenario=scenario_columns(),
        entities=entity_seeds(),
        facts=[],
        conditions=[to_condition(cond) for cond in ordered_conditions()],
        end_conditions=[],
        invariants=[],
        minigames=[],
        rule_checks=[],
        sheet_rules=[],
        maps=maps.map_seeds(),
    )
