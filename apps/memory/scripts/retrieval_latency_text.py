"""Pure text generators for the retrieval latency corpora."""

import random
from dataclasses import dataclass

ONSETS = [
    "Al", "Br", "Cal", "Dor", "El", "Fen", "Gar", "Hal", "Ir", "Jor",
    "Kel", "Lor", "Mar", "Nar", "Os", "Per", "Quil", "Ren", "Sol", "Tor",
]  # fmt: skip
VOWELS = ["a", "e", "i", "o", "u", "ae", "io", "ei"]
CODAS = ["n", "s", "th", "ric", "wyn", "dus"]
SURNAMES = [
    "Ashford", "Blackwood", "Crowley", "Dunmere", "Everhart", "Fairwind",
    "Grimshaw", "Hollow", "Ironside", "Kestrel", "Larkspur", "Mistral",
    "Northcott", "Oakenshield", "Pyke", "Quarrel", "Ravenscar", "Stormvale",
    "Thornfield", "Underhill", "Valemont", "Whitlock", "Yarrow", "Zephyr",
]  # fmt: skip
EPITHETS = [
    "Grey Warden", "Silent Blade", "Iron Regent", "Pale Oracle", "Red Envoy",
    "Broken Crown", "Last Ferryman", "Hollow Saint", "Night Herald",
    "Gilded Fox", "Tide Keeper", "Ash Prophet", "Lantern Bearer",
]  # fmt: skip
LORE_VOCABULARY = [
    "river", "king", "war", "gold", "shadow", "storm", "harbor", "temple",
    "oath", "silver", "blade", "council", "winter", "market", "tower", "ferry",
    "forest", "plague", "crown", "ember", "vault", "banner", "smuggler",
    "priest", "harvest", "bridge", "cellar", "lantern", "prophecy", "ruin",
    "caravan", "orchard", "garrison", "tavern", "signet", "famine", "coast",
    "glacier", "archive", "beacon", "cavern", "dagger", "exile", "fortress",
    "guild", "heir", "island", "jewel", "knight", "ledger", "mirror", "night",
    "ocean", "pilgrim", "quarry", "rebellion", "scroll", "throne", "treaty",
    "valley", "well", "wolf", "yield", "kingdom", "sword", "dragon", "magic",
]  # fmt: skip
SENTENCE_VERBS = [
    "guards", "remembers", "abandoned", "quarrels over", "hides", "shelters",
    "bargains for", "mourns", "defends", "burned", "whispers about",
]  # fmt: skip
RELATION_PREDICATES = [
    "allied_with", "rivals", "serves", "protects", "owes_debt_to", "trades_with",
]  # fmt: skip
ATTRIBUTE_PREDICATES = ["occupation", "appearance", "secret", "homeland", "grudge"]
ACTION_OPENINGS = ["I ask", "I turn to", "I warn", "I bargain with", "I follow"]
PRONOUN_ACTIONS = ["I ask her again", "I press him for more", "I ask them once more"]
ENTITY_TYPES = ["character", "location", "faction"]
SENTENCES_PER_PARAGRAPH = 3
WORDS_PER_SENTENCE = 6


@dataclass(frozen=True)
class EntityName:
    canonical: str
    aliases: tuple[str, ...]
    entity_type: str


def _first_name(index: int) -> str:
    onset = ONSETS[index % len(ONSETS)]
    vowel = VOWELS[(index // len(ONSETS)) % len(VOWELS)]
    coda = CODAS[(index // (len(ONSETS) * len(VOWELS))) % len(CODAS)]
    return f"{onset}{vowel}{coda}"


def build_entity_name(index: int) -> EntityName:
    first = _first_name(index)
    canonical = f"{first} {SURNAMES[index % len(SURNAMES)]}"
    aliases = [first]
    if index % 3 == 0:
        aliases.append(f"the {EPITHETS[index % len(EPITHETS)]}")
    return EntityName(
        canonical, tuple(aliases), ENTITY_TYPES[index % len(ENTITY_TYPES)]
    )


def lore_paragraph(rng: random.Random, mentions: list[str]) -> str:
    sentences = []
    for position in range(SENTENCES_PER_PARAGRAPH):
        words = rng.sample(LORE_VOCABULARY, WORDS_PER_SENTENCE)
        subject = mentions[position % len(mentions)] if mentions else words.pop()
        verb = rng.choice(SENTENCE_VERBS)
        sentences.append(
            f"The {words[0]} of {subject} {verb} the {' '.join(words[1:])}."
        )
    return " ".join(sentences)


def attribute_value(rng: random.Random) -> str:
    return " ".join(rng.sample(LORE_VOCABULARY, 2))


def turn_action(rng: random.Random, name: str) -> str:
    return (
        f"{rng.choice(ACTION_OPENINGS)} {name} about the {rng.choice(LORE_VOCABULARY)}."
    )
