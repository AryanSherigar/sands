"""Prompts for the letter scene: the sender's letter, the player's scribe and the reply."""

from app.services.letter_prompt_text import (
    LETTER_ACK_DIRECTIVE,
    LETTER_DECISION_DIRECTIVE,
    SCRIBE_REQUEST_DIRECTIVE,
    SCRIBE_RULES,
    letter_topic,
)
from app.services.scene_prompt import _progress, _text_content, quote_player
from google.genai import types
from strategy_contracts.scene import ScenePackage
from strategy_contracts.scene_exchange import SceneExchangeView


def _open_turn(package: ScenePackage) -> str:
    return (
        f"Write the letter now. It concerns: {letter_topic(package)}. Three to five "
        "sentences, in your own voice. Do not mention your private brief."
    )


def _incoming_letter(transcript: list[SceneExchangeView]) -> str:
    return transcript[0].leader_text


def _letter_history(
    package: ScenePackage, transcript: list[SceneExchangeView]
) -> list[types.Content]:
    return [
        _text_content("user", _open_turn(package)),
        _text_content("model", _incoming_letter(transcript)),
    ]


def build_scribe_system_instruction(package: ScenePackage) -> str:
    facts = "\n".join(
        f"- {fact.label}: {fact.value}" for fact in package.situation.facts
    )
    sender = next(item for item in package.participants if item.kind.value == "leader")
    return (
        f"{SCRIBE_RULES}\n\nSITUATION\n{package.situation.summary}\n{facts}\n\n"
        f"THE LETTER IS FROM\n{sender.name}"
    )


def build_letter_open_contents(package: ScenePackage) -> list[types.Content]:
    return [_text_content("user", _open_turn(package))]


def build_letter_scribe_contents(
    package: ScenePackage,
    transcript: list[SceneExchangeView],
    instruction: str,
    current_draft: str,
) -> list[types.Content]:
    tail = (
        f"The letter that arrived:\n{_incoming_letter(transcript)}\n\n"
        f"The ruler's instruction:\n{quote_player(instruction)}\n\n"
        f"The current draft:\n{quote_player(current_draft)}\n\n"
        f"{SCRIBE_REQUEST_DIRECTIVE}"
    )
    return [_text_content("user", tail)]


def build_letter_ack_contents(
    package: ScenePackage, transcript: list[SceneExchangeView], sealed_prose: str
) -> list[types.Content]:
    tail = f"{quote_player(sealed_prose)}\n\n{LETTER_ACK_DIRECTIVE}"
    return [*_letter_history(package, transcript), _text_content("user", tail)]


def build_letter_decision_contents(
    package: ScenePackage,
    transcript: list[SceneExchangeView],
    sealed_prose: str,
    acknowledgement: str,
) -> list[types.Content]:
    progress = _progress(len(transcript) + 1, package.exchange_cap)
    return [
        *_letter_history(package, transcript),
        _text_content("user", quote_player(sealed_prose)),
        _text_content("model", acknowledgement),
        _text_content("user", f"{progress} {LETTER_DECISION_DIRECTIVE}"),
    ]
