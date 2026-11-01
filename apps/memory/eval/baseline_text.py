"""What the narrator sees with memory off, mirroring TRS `context_assembly` (not importable)."""

import math
from dataclasses import dataclass

from eval.corpus_loader import Campaign
from eval.corpus_models import ProbeDef
from eval.payloads import render_recent_text
from eval.scoring.retrieval import Chunk

# NOTE: constants mirror turn-resolution-service/app/config.py; test_baseline_text pins them.
CHARS_PER_TOKEN = 3
LORE_FALLBACK_TOKENS = 1500
RECENT_WINDOW_TURNS = 6
ACTIVE_CARD_CAP = 6
ACTIVE_CARD_TOKENS = 1200
PARAGRAPH_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class InlineText:
    window_text: str
    lore_chunks: list[Chunk]


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def _essentials(campaign: Campaign, at_turn: int) -> str:
    scenario = campaign.scenario
    lines = []
    if scenario.main_conflict:
        lines.append(f"- Main conflict: {scenario.main_conflict}")
    if scenario.opening_prompt and at_turn < RECENT_WINDOW_TURNS:
        lines.append(f"- Opening scene: {scenario.opening_prompt}")
    return "\n".join(lines)


def _lore_paragraphs(campaign: Campaign) -> list[str]:
    scenario = campaign.scenario
    paragraphs: list[str] = []
    for text in (scenario.world_lore, scenario.single_lore_prompt):
        paragraphs.extend(
            p.strip() for p in text.split(PARAGRAPH_SEPARATOR) if p.strip()
        )
    return paragraphs


def lore_fallback_chunks(campaign: Campaign) -> list[Chunk]:
    """Whole paragraphs up to the budget; newbie mode only, never story cards."""
    if campaign.scenario.mode == "master":
        return []
    kept: list[Chunk] = []
    used = 0
    for paragraph in _lore_paragraphs(campaign):
        cost = estimate_tokens(paragraph)
        if used + cost > LORE_FALLBACK_TOKENS:
            break
        kept.append(Chunk(paragraph, cost, (), "lore"))
        used += cost
    return kept


def _scene_cards(campaign: Campaign, probe: ProbeDef) -> list[str]:
    if campaign.scenario.mode != "master":
        return []
    scene_keys = set(campaign.turns[probe.at_turn - 1].snapshot.scene_entity_keys)
    lowered_action = probe.action_text.lower()
    entities = [
        e
        for e in campaign.scenario.entities
        if e.key in scene_keys and not e.is_player and e.description
    ]
    entities.sort(key=lambda e: e.canonical_name.lower() not in lowered_action)
    kept: list[str] = []
    used = 0
    for entity in entities[:ACTIVE_CARD_CAP]:
        text = f"{entity.canonical_name} ({entity.entity_type}): {entity.description}"
        used += estimate_tokens(text)
        if used > ACTIVE_CARD_TOKENS:
            break
        kept.append(text)
    return kept


def build_inline_text(campaign: Campaign, probe: ProbeDef) -> InlineText:
    blocks = [
        _essentials(campaign, probe.at_turn),
        *_scene_cards(campaign, probe),
        render_recent_text(campaign.turns, probe.at_turn),
    ]
    return InlineText(
        window_text=PARAGRAPH_SEPARATOR.join(block for block in blocks if block),
        lore_chunks=lore_fallback_chunks(campaign),
    )
