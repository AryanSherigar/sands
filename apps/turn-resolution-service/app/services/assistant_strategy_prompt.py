"""Prompt text and context formatting for the strategy-mode Studio assistant."""

import json

from app.models.assistant import AssistantStrategyContext

STRATEGY_CONTEXT_HEADING = "CURRENT STRATEGY SCENARIO DATA:"

STRATEGY_BASE_PERSONA = (
    "You are a grand-strategy scenario designer helping a creator author a "
    "turn-based strategy scenario: factions and their rulers, a region map, "
    "who owns what at the start, who is at war or at peace, grudges and "
    "claims, starting armies, the calendar, and diplomacy rules. You care "
    "about playability: at least two factions, each with a capital and "
    "territory, believable tension between neighbours, and a start that gives "
    "the player a real choice. You never invent ids: you only reference "
    "faction, leader, region and army ids listed in the scenario data."
)

STRATEGY_ACTION_SYNTAX_GUIDE = (
    "\n\nACTION BLOCKS:\n"
    "When you propose concrete changes the creator can apply, put each one in "
    "its own code block with an action tag. Block content must be valid JSON "
    "of the shape shown, except title. Every id must come from the scenario "
    "data or from a temp_id you assigned in the same reply.\n"
    '- ```action:faction\\n{"temp_id": "<short key>", "name": "<name>", '
    '"capital_region_id": "<region id or null>", "leader_name": "<ruler name>", '
    '"leader_history": "<optional backstory>", "treasury": 100, '
    '"manpower": 400, "stability": 60, "is_playable": false}\\n```\n'
    '- ```action:leader_history\\n{"leader_id": "<leader id>", '
    '"history": "<backstory>"}\\n```\n'
    '- ```action:relation\\n{"faction_a": "<faction id>", '
    '"faction_b": "<faction id>", "status": "war"|"peace"|"alliance"}\\n```\n'
    '- ```action:claim\\n{"faction_id": "<faction id>", '
    '"region_id": "<region id>"}\\n```\n'
    '- ```action:grudge\\n{"holder_id": "<leader id>", "target_id": '
    '"<leader id>", "opinion": -100..100, "reason": "<why>"}\\n```\n'
    '- ```action:region_setup\\n{"region_id": "<region id>", '
    '"owner_id": "<faction id or null>", "population": 0, "wealth": 0, '
    '"manpower": 0, "unrest": 0..100, "garrison": 0}\\n```\n'
    '- ```action:army\\n{"owner_id": "<faction id>", "location_id": '
    '"<region id>", "troops": {"infantry": 0, "cavalry": 0, '
    '"archers_siege": 0}, "commander_name": "<optional>"}\\n```\n'
    '- ```action:timing\\n{"start_year": 1000, "start_month": 1..12, '
    '"end_year": 1004}\\n```\n'
    '- ```action:rules\\n{"agents_enabled": true, "revolt_talks_enabled": '
    'true, "bribe_base_price": 0, "trade_value_per_turn": 1, '
    '"trade_income_percent": 1, "access_value_per_turn": 1, '
    '"conditional_trigger_percent": 0..200, "conditional_gate_percent": '
    '0..200, "oath_offer_min_opinion": 0, "oath_offer_duration_turns": 1, '
    '"letters_enabled": true, "letter_cooldown_turns": 1, '
    '"judgments_enabled": true, "judgment_cooldown_turns": 1, '
    '"judgment_sentence_turns": 1}'
    "\\n```\n"
    "- ```action:title\\n<scenario title>\\n```\n\n"
    'A new faction\'s ruler can be referred to as "<temp_id>_ruler" in leader_history and grudge blocks of the same reply. A rules block may include only the keys that change. Map geometry and '
    "art are edited elsewhere and cannot be proposed. Use normal markdown for "
    "discussion and feedback; use action blocks only for ready-to-apply changes."
)


def _format_timing(context: AssistantStrategyContext) -> str:
    if context.timing is None:
        return "Calendar: (not set)"
    timing = context.timing
    return (
        f"Calendar: starts {timing.start_year}-{timing.start_month:02d}, "
        f"ends {timing.end_year}"
    )


def _format_factions(context: AssistantStrategyContext) -> str:
    if not context.factions:
        return "Factions: (none yet)"
    lines = [
        f"- {f.faction_id}: {f.name} | leader {f.leader_id or '-'} "
        f"({f.leader_name or 'unnamed'}) | capital {f.capital_region_id or '-'} "
        f"| treasury {f.treasury}, manpower {f.manpower}, stability {f.stability}"
        f"{' | playable' if f.is_playable else ''}"
        + (f"\n  history: {f.leader_history}" if f.leader_history else "")
        for f in sorted(context.factions, key=lambda item: item.faction_id)
    ]
    return "Factions:\n" + "\n".join(lines)


def _format_regions(context: AssistantStrategyContext) -> str:
    if not context.regions:
        return "Regions: (no map yet)"
    lines = [
        f"- {r.region_id}: {r.name or '(unnamed)'} | owner {r.owner_id or '-'} "
        f"| pop {r.population}, wealth {r.wealth}, manpower {r.manpower}, "
        f"unrest {r.unrest}, garrison {r.garrison}"
        for r in sorted(context.regions, key=lambda item: item.region_id)
    ]
    return "Regions:\n" + "\n".join(lines)


def _format_diplomacy(context: AssistantStrategyContext) -> list[str]:
    sections: list[str] = []
    if context.relations:
        relations = [
            f"- {r.faction_a} / {r.faction_b}: {r.status}"
            for r in sorted(context.relations, key=lambda i: (i.faction_a, i.faction_b))
        ]
        sections.append("Relations:\n" + "\n".join(relations))
    if context.claims:
        claims = [
            f"- {c.faction_id} claims {c.region_id}"
            for c in sorted(context.claims, key=lambda i: (i.faction_id, i.region_id))
        ]
        sections.append("Claims:\n" + "\n".join(claims))
    if context.grudges:
        grudges = [
            f"- {g.holder_id} -> {g.target_id}: {g.opinion} ({g.reason or 'no reason'})"
            for g in sorted(context.grudges, key=lambda i: (i.holder_id, i.target_id))
        ]
        sections.append("Grudges:\n" + "\n".join(grudges))
    return sections


def _format_armies(context: AssistantStrategyContext) -> str:
    if not context.armies:
        return "Armies: (none)"
    lines = [
        f"- {a.army_id}: {a.owner_id} at {a.location_id} | "
        f"troops {json.dumps(a.troops, sort_keys=True)}"
        f"{' | commander ' + a.commander_name if a.commander_name else ''}"
        for a in sorted(context.armies, key=lambda item: item.army_id)
    ]
    return "Armies:\n" + "\n".join(lines)


def format_strategy_context(context: AssistantStrategyContext) -> str:
    lines = [
        f"Title: {context.title or '(Untitled)'}",
        _format_timing(context),
        _format_factions(context),
        _format_regions(context),
        *_format_diplomacy(context),
        _format_armies(context),
    ]
    if context.rules:
        lines.append("Rules: " + json.dumps(context.rules, sort_keys=True))
    if context.active_panel:
        lines.append(f"Open panel: {context.active_panel}")
    return "\n".join(lines)
