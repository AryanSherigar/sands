"""Prompts for the judgment scene: the opening tableau, the court's replies and the closing.

ADR-21 ordering: the system instruction (rules, situation, accused, court) comes first and
never changes within a scene; the opening exchange and each earlier exchange follow in
order; the per-turn directive and the sovereign's words come last.
"""

from app.services.judgment_prompt_text import (
    CLOSING_DIRECTIVE,
    JUDGMENT_RULES,
    NO_DECREE_NOTE,
    OPEN_DIRECTIVE,
    REPLY_DIRECTIVE,
    STANCE_TEXT,
)
from app.services.scene_prompt import _progress, _text_content, quote_player
from google.genai import types
from strategy_contracts.judgment import AdvisorStance
from strategy_contracts.scene import Participant, ScenePackage
from strategy_contracts.scene_exchange import SceneExchangeView


def _accused_block(accused: Participant) -> str:
    traits = ", ".join(accused.trait_ids) or "none"
    notes = " ".join(accused.trait_notes)
    return (
        f"{accused.name}. Traits: {traits}. {notes}\n"
        f"Bearing before the sovereign: {accused.mood or 'composed'}."
    )


def _advisor_line(advisor: Participant) -> str:
    stance = STANCE_TEXT[advisor.stance or AdvisorStance.NEUTRAL]
    notes = " ".join(advisor.trait_notes)
    return f"- {advisor.name}: {stance}. {notes}".rstrip()


def build_judgment_system_instruction(package: ScenePackage) -> str:
    facts = "\n".join(
        f"- {fact.label}: {fact.value}" for fact in package.situation.facts
    )
    accused, *advisors = package.participants
    court = (
        "\n".join(_advisor_line(item) for item in advisors)
        or "- no one speaks for them"
    )
    return (
        f"{JUDGMENT_RULES}\n\nSITUATION\n{package.situation.summary}\n{facts}\n\n"
        f"THE ACCUSED\n{_accused_block(accused)}\n\nTHE COURT\n{court}"
    )


def build_judgment_open_contents(package: ScenePackage) -> list[types.Content]:
    return [_text_content("user", OPEN_DIRECTIVE)]


def _history(transcript: list[SceneExchangeView]) -> list[types.Content]:
    contents = [
        _text_content("user", OPEN_DIRECTIVE),
        _text_content("model", transcript[0].leader_text),
    ]
    for exchange in transcript[1:]:
        contents.append(_text_content("user", quote_player(exchange.player_text)))
        contents.append(_text_content("model", exchange.leader_text))
    return contents


def build_judgment_reply_contents(
    package: ScenePackage, transcript: list[SceneExchangeView], player_text: str
) -> list[types.Content]:
    progress = _progress(len(transcript) + 1, package.exchange_cap)
    tail = f"{quote_player(player_text)}\n\n{progress} {REPLY_DIRECTIVE}"
    return [*_history(transcript), _text_content("user", tail)]


def build_judgment_closing_contents(
    package: ScenePackage,
    transcript: list[SceneExchangeView],
    verdict: str,
    nuance: str | None,
    decree_text: str,
) -> list[types.Content]:
    sentence = verdict if nuance is None else f"{verdict}, {nuance.replace('_', ' ')}"
    words = quote_player(decree_text) if decree_text.strip() else NO_DECREE_NOTE
    tail = f"The sovereign has pronounced: {sentence}.\n{words}\n\n{CLOSING_DIRECTIVE}"
    return [*_history(transcript), _text_content("user", tail)]
