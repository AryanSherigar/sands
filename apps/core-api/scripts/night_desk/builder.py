"""Assembles the whole scenario in the order the evaluator must see it."""

from dataclasses import dataclass

from app.models.condition import ConditionCreate
from app.models.end_condition import EndConditionCreate
from app.models.fact import FactCreate
from app.models.invariant import InvariantCreate
from app.models.minigame import MinigameCreate
from app.models.rule_check import RuleCheckCreate
from app.models.sheet_rule import SheetRuleCreate
from scripts.night_desk import prose, schema
from scripts.night_desk.checks import rule_checks
from scripts.night_desk.conditions import (
    backstops,
    clock,
    events,
    facts,
    fragments,
    handlers,
    instructions,
    visitors,
)
from scripts.night_desk.endings import end_conditions
from scripts.night_desk.entities import EntitySeed, entity_seeds, fact_seeds
from scripts.night_desk.expr import Cond, to_condition
from scripts.night_desk.invariants import invariants
from scripts.night_desk.minigames import minigames
from scripts.night_desk.sheet_rules import sheet_rules

ACTION_CHIPS = ["Check the Log", "File a folder", "Look around", "Wait"]
PLAYTIME = "20m"
NAME_FIELD = {"key": "character_name", "label": "Your name", "is_character_name": True}
ENABLED_TOOLS = ["rule_checks", "rule_sheet", "status_hud", "atmosphere", "composure"]

# NOTE: Group order is part of the design (data doc §5); validation enforces it.
GROUP_ORDER = ("E", "H", "V", "P", "F", "D", "T", "N", "A")


@dataclass(frozen=True)
class NightDeskScenario:
    scenario: dict[str, object]
    entities: list[EntitySeed]
    facts: list[FactCreate]
    conditions: list[ConditionCreate]
    end_conditions: list[EndConditionCreate]
    invariants: list[InvariantCreate]
    minigames: list[MinigameCreate]
    rule_checks: list[RuleCheckCreate]
    sheet_rules: list[SheetRuleCreate]


def ordered_conditions() -> list[Cond]:
    return [
        *events.timed_events(),
        *handlers.result_handlers(),
        *visitors.visitor_presence(),
        *backstops.backstops(),
        *fragments.fragment_pipeline(),
        *clock.drains(),
        *instructions.act_instructions(),
        *instructions.sanity_tiers(),
        *instructions.seed_tells(),
        *instructions.rule_facts(),
        *instructions.ambient_details(),
        *facts.never_describe(),
        *clock.advance(),
    ]


def narrator_persona() -> str:
    return prose.PERSONA


def opening_prompt() -> str:
    return prose.OPENING_SCENE.replace("{player_name}", prose.OPENING_FALLBACK_NAME)


def scenario_columns() -> dict[str, object]:
    return {
        "title": prose.TITLE,
        "logline": prose.LOGLINE,
        "mode": "master",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["rules-horror", "psychological", "liminal"],
        "content_tag": "mature",
        "content_tags": ["horror-themes", "psychological-tension"],
        "is_mature": True,
        "estimated_playtime": PLAYTIME,
        "narrator_persona": narrator_persona(),
        "opening_scene": prose.OPENING_SCENE,
        "world_data": {
            "openingPrompt": opening_prompt(),
            "presentation": {"welcome_tape_id": "tallis-v1"},
            "fallback_narration": prose.FALLBACK_NARRATION,
            "escalation_reply": prose.ESCALATION_REPLY,
            "duties": list(prose.DUTIES),
        },
        "setup_schema": [NAME_FIELD],
        "state_schema": schema.build_state_schema(),
        "checkpoints": [],
        "rules": {},
        "action_chips": ACTION_CHIPS,
        "enabled_tools": list(ENABLED_TOOLS),
    }


def build() -> NightDeskScenario:
    return NightDeskScenario(
        scenario=scenario_columns(),
        entities=entity_seeds(),
        facts=fact_seeds(),
        conditions=[to_condition(cond) for cond in ordered_conditions()],
        end_conditions=end_conditions(),
        invariants=invariants(),
        minigames=minigames(),
        rule_checks=rule_checks(),
        sheet_rules=sheet_rules(),
    )
