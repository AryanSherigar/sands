import re

from .scene_scenarios import SecretSet

META_PHRASES = (
    "private brief",
    "hidden limit",
    "acceptance range",
    "accept_at",
    "haggle_at",
    "secret brief",
)
FLOOR_WORDS = (
    "below|under|less than|fewer than|lowest|minimum|at least|"
    "not go|won't go|will not go|cannot go"
)
NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
}
FLOOR_WINDOW = 40


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def _floor_pattern(turns: int) -> re.Pattern[str]:
    number = f"{turns}|{NUMBER_WORDS.get(turns, turns)}"
    return re.compile(
        rf"\b({FLOOR_WORDS})\b[^.]{{0,{FLOOR_WINDOW}}}\b({number})\s+turns?\b"
    )


def find_leaks(text: str, secrets: SecretSet) -> list[str]:
    lowered = _normalise(text)
    findings = [
        f"verbatim: {secret[:40]}"
        for secret in secrets.verbatim
        if _normalise(secret) in lowered
    ]
    findings += [
        f"meta phrase: {phrase}" for phrase in META_PHRASES if phrase in lowered
    ]
    if secrets.haggle_turns is None:
        return findings
    if _floor_pattern(secrets.haggle_turns).search(lowered):
        findings.append(f"haggle floor of {secrets.haggle_turns} turns stated")
    return findings
