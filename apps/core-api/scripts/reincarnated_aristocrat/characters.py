"""The ten canon characters: stats, hidden caps, aptitudes and personality.

Wiki cap numbers (fan wiki, end-of-story values) are used where it lists them
(Ritsu, Charlotte, Rosell, Mireille); every other number, and every starting
value, is an estimate made for this scenario and flagged for the owner's review.
Ages are written as an offset from Ars's age so the narrator can state them from
one tracked number.
"""

from dataclasses import dataclass

from app.models.entity import AttributeFieldSchema, EntityCreate
from scripts.reincarnated_aristocrat import stats
from scripts.reincarnated_aristocrat.stats import StatSpec
from scripts.seeding.types import EntitySeed

TRAIT_NOTES = {
    "devoted": "Quietly loyal; shows it through small acts, not speeches.",
    "ambitious": "Hungry to rise; weighs every ruler by what he can offer.",
    "proud": "Touchy about rank and slights; hides hurt behind composure.",
    "timid": "Hesitant and easily frightened; opens up to kindness.",
    "pragmatic": "Follows results; unsentimental but fair.",
    "idealist": "Judges a ruler by how he treats the weak.",
}
PRONOUNS = {
    "ritsu": "she/her",
    "charlotte": "she/her",
    "rosell": "he/him",
    "lysia": "she/her",
    "mireille": "she/her",
    "fahm": "she/her",
    "raven": "he/him",
    "sofia": "she/her",
    "kreiz": "he/him",
    "wren": "she/her",
}
APPRAISAL_NOTE = (
    "Never state this character's stat numbers, aptitudes or loyalty unless an "
    "appraisal instruction is active."
)


@dataclass(frozen=True)
class CharacterSpec:
    slug: str
    name: str
    description: str
    trait: str
    age_offset: int
    is_adult: bool
    is_recruitable: bool
    stats: dict[str, StatSpec]
    aptitudes: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    loyalty: int = stats.INITIAL_LOYALTY
    voice: str = ""


def _stats(
    leadership: tuple[int, int | None],
    prowess: tuple[int, int | None],
    ingenuity: tuple[int, int | None],
    politics: tuple[int, int | None],
    courage: tuple[int, int | None],
    ambition: int,
) -> dict[str, StatSpec]:
    return {
        "leadership": StatSpec(*leadership),
        "prowess": StatSpec(*prowess),
        "ingenuity": StatSpec(*ingenuity),
        "politics": StatSpec(*politics),
        "courage": StatSpec(*courage),
        "ambition": StatSpec(ambition),
    }


CHARACTERS: tuple[CharacterSpec, ...] = (
    CharacterSpec(
        "ritsu",
        "Ritsu Muses",
        "An orphan of the Marca people, shunned in Lamberk and wary of kindness.",
        "devoted",
        4,
        False,
        True,
        _stats((30, 99), (38, 90), (28, 99), (12, 100), (55, None), 21),
        ("A", "S", "A", "C", "S", "A", "D", "C", "S"),
        ("Reitz",),
        voice="Short, guarded sentences; softens only once trusted.",
    ),
    CharacterSpec(
        "charlotte",
        "Charlotte Wraith",
        "A girl sold to slave traders, quiet and underfed, with a stillness that is not only fear.",
        "devoted",
        3,
        False,
        True,
        _stats((20, 92), (40, 116), (18, 45), (10, 40), (40, None), 1),
        ("D", "D", "D", "S", "D", "D", "D", "D", "D"),
        ("Charlotte Reis",),
        voice="Barely speaks at first; honest to a fault.",
    ),
    CharacterSpec(
        "rosell",
        "Rosell Kischa",
        "A child of the territory who always seems to be thinking three moves ahead.",
        "pragmatic",
        2,
        False,
        True,
        _stats((12, None), (8, None), (52, 109), (20, None), (20, None), 20),
        ("D", "D", "C", "C", "A", "A", "C", "A", "S"),
        ("Kischa Rosell",),
        voice="Precise and a little too logical; asks why before agreeing.",
    ),
    CharacterSpec(
        "lysia",
        "Lysia Plaid",
        "Daughter of Lord Hamand Plaid of Torbekistan, promised to Ars before either could walk.",
        "ambitious",
        1,
        False,
        True,
        _stats((15, None), (5, None), (40, None), (62, None), (25, None), 80),
        ("E", "E", "E", "D", "E", "E", "E", "E", "B"),
        ("Lisia",),
        voice="Poised and courteous; every kindness has a purpose behind it.",
    ),
    CharacterSpec(
        "mireille",
        "Mireille Grangeon",
        "A former noble who drifts from tavern to tavern, spending what is left of her savings.",
        "proud",
        19,
        True,
        True,
        _stats((70, 98), (35, None), (85, 103), (60, None), (60, 72), 100),
        ("C", "C", "C", "C", "C", "D", "D", "D", "S"),
        ("Mireilla Grangeon",),
        voice="Wry and unhurried; talks like someone who has been rich and has been wrong.",
    ),
    CharacterSpec(
        "fahm",
        "Fahm",
        "Leader of a mercenary band called the Shadows, often hiding in plain sight as a tavern waitress.",
        "pragmatic",
        14,
        True,
        True,
        _stats((35, None), (55, None), (50, None), (40, None), (65, None), 30),
        ("C", "D", "B", "A", "D", "C", "D", "D", "B"),
        ("the Shadows' leader",),
        voice="Light and teasing on the surface; counts exits as he talks.",
    ),
    CharacterSpec(
        "raven",
        "Raven Louvent",
        "Lord of Lamberk, a farmer's son who rose by the sword. Loved by his household.",
        "idealist",
        29,
        True,
        False,
        _stats((62, None), (78, None), (35, None), (40, None), (85, None), 15),
        ("A", "B", "C", "E", "D", "C", "E", "E", "C"),
        ("Father", "Lord Raven"),
        loyalty=90,
        voice="Warm and plain-spoken; praises in public and corrects in private.",
    ),
    CharacterSpec(
        "sofia",
        "Sofia Louvent",
        "Ars's mother.",
        "devoted",
        24,
        True,
        False,
        _stats((15, None), (5, None), (30, None), (35, None), (30, None), 10),
        ("E", "E", "E", "E", "E", "E", "E", "E", "D"),
        ("Mother",),
        loyalty=90,
        voice="Gentle and watchful; worry shows in what she does not say.",
    ),
    CharacterSpec(
        "kreiz",
        "Kreiz Louvent",
        "Ars's younger brother.",
        "timid",
        -2,
        False,
        False,
        _stats((10, None), (10, None), (20, None), (15, None), (25, None), 25),
        ("D", "D", "D", "D", "D", "D", "E", "E", "D"),
        ("Kreiz",),
        loyalty=70,
        voice="Quick to follow Ars around; quicker to hide behind him.",
    ),
    CharacterSpec(
        "wren",
        "Wren Louvent",
        "Ars's younger sister.",
        "devoted",
        -4,
        False,
        False,
        _stats((8, None), (5, None), (25, None), (20, None), (30, None), 20),
        ("E", "E", "D", "D", "D", "D", "E", "E", "D"),
        ("Wren",),
        loyalty=80,
        voice="Bright and direct; says what the grown-ups are thinking.",
    ),
)

WIKI_CAP_SLUGS = frozenset({"ritsu", "charlotte", "rosell", "mireille"})
RECRUITABLE_SLUGS = tuple(item.slug for item in CHARACTERS if item.is_recruitable)
CHARACTER_SLUGS = tuple(item.slug for item in CHARACTERS)


def _plain_field(
    kind: str, initial: object, label: str, is_narrator_visible: bool = False
) -> AttributeFieldSchema:
    return AttributeFieldSchema(
        type=kind,
        initial=initial,
        label=label,
        is_narrator_visible=is_narrator_visible,
    )


def attributes_schema(spec: CharacterSpec) -> dict[str, AttributeFieldSchema]:
    schema = dict(
        stats.stat_field(key, value, spec.is_adult) for key, value in spec.stats.items()
    )
    for key, rank in zip(stats.APTITUDE_KEYS, spec.aptitudes, strict=True):
        schema[key] = _plain_field("string", rank, stats.APTITUDE_LABELS[key])
    schema["loyalty"] = AttributeFieldSchema(
        type="number",
        initial=spec.loyalty,
        min=stats.STAT_FLOOR,
        max=stats.PERCENT_CEILING,
        label="Loyalty",
        is_narrator_visible=True,
    )
    schema["is_recruited"] = _plain_field("boolean", False, "Is recruited")
    schema["is_appraised"] = _plain_field("boolean", False, "Is appraised")
    schema["has_trained"] = _plain_field("boolean", False, "Has trained")
    schema["betrayal_risk"] = _plain_field("boolean", False, "Betrayal risk")
    schema["role"] = _plain_field("string", "", "Role")
    return schema


def aptitude_line(spec: CharacterSpec) -> str:
    pairs = zip(stats.APTITUDE_KEYS, spec.aptitudes, strict=True)
    return ", ".join(f"{stats.APTITUDE_LABELS[key]} {rank}" for key, rank in pairs)


def age_note(spec: CharacterSpec) -> str:
    if spec.age_offset == 0:
        return "Age: the same as Ars's age."
    return f"Age: Ars's age {spec.age_offset:+d}."


def narrator_instruction(spec: CharacterSpec) -> str:
    parts = (
        f"Trait: {spec.trait}. {TRAIT_NOTES[spec.trait]}",
        f"Voice: {spec.voice}",
        age_note(spec),
        f"Aptitudes: {aptitude_line(spec)}.",
        APPRAISAL_NOTE,
    )
    return " ".join(parts)


def entity_seed(spec: CharacterSpec) -> EntitySeed:
    return EntitySeed(
        spec.slug,
        EntityCreate(
            entity_type="character",
            canonical_name=spec.name,
            aliases=list(spec.aliases),
            description=spec.description,
            attributes_schema=attributes_schema(spec),
            narrator_instruction=narrator_instruction(spec),
        ),
    )


def character_seeds() -> list[EntitySeed]:
    return [entity_seed(spec) for spec in CHARACTERS]
