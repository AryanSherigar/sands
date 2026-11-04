"""World entities and the visible facts (scenario doc §5, data doc §2).

Canon (the hidden backstory) is never stored as facts; fragments reach the
narrator only through the pulse in conditions/fragments.py.
"""

from app.models.entity import AttributeFieldSchema, EntityCreate
from app.models.fact import FactCreate
from scripts.night_desk.ids import entity_id
from scripts.seeding.types import EntitySeed

MOVEMENT_CLASS_FIELD = "movement_class"
MOVEMENT_CLASS_APPROACH = "approach"
MOVEMENT_CLASS_INTERIOR = "interior"

# NOTE: "Cabin 14" and "the cabin" are shared by the approach and the interior
# on purpose: the verb the player types ("go to" vs "enter") picks which one.
CABIN_ALIASES = ["Cabin 14", "the cabin"]
LOCATION_ALIASES: dict[str, list[str]] = {
    "elevator_lobby": ["the lobby", "the elevator", "the poster"],
    "night_desk": ["the desk"],
    "east_corridor": ["the corridor"],
    "east_alcove": ["the alcove", "the vending machine"],
    "records_room": ["Records", "the records room", "the filing room"],
    "cabin_approach": CABIN_ALIASES,
    "cabin_14": CABIN_ALIASES,
    "print_room": ["the print room", "the printer"],
    "stairwell_door": ["the stairwell"],
}
LOCATION_MOVEMENT_CLASS: dict[str, str] = {
    "cabin_approach": MOVEMENT_CLASS_APPROACH,
    "cabin_14": MOVEMENT_CLASS_INTERIOR,
}


def _movement_attributes(slug: str) -> dict[str, AttributeFieldSchema]:
    movement_class = LOCATION_MOVEMENT_CLASS.get(slug)
    if movement_class is None:
        return {}
    return {
        MOVEMENT_CLASS_FIELD: AttributeFieldSchema(type="enum", initial=movement_class)
    }


def _entity(
    slug: str,
    entity_type: str,
    name: str,
    description: str,
    obtainable: bool | None = None,
) -> EntitySeed:
    return EntitySeed(
        slug,
        EntityCreate(
            entity_type=entity_type,
            canonical_name=name,
            aliases=LOCATION_ALIASES.get(slug, []),
            description=description,
            obtainable=obtainable,
            attributes_schema=_movement_attributes(slug),
        ),
    )


ENTITY_ROWS: tuple[tuple[str | bool, ...], ...] = (
    (
        "tallis_and_orr",
        "organization",
        "Tallis & Orr",
        "The company. Night Records Desk, Floor 9.",
    ),
    (
        "eva_venn",
        "character",
        "Eva Venn",
        "The outgoing night clerk. A voice, a voicemail and handwriting after the hand-off.",
    ),
    (
        "visitor_margaret",
        "character",
        "Margaret Hale",
        "Around 80, a cardigan, slippers under her coat. A grey folder, a white band on one wrist.",
    ),
    (
        "visitor_daniel",
        "character",
        "Daniel Osei",
        "In his forties, a work lanyard still round his neck. A grey folder, a white band on one wrist.",
    ),
    (
        "visitor_ruth",
        "character",
        "Ruth Ellery",
        "In her sixties, a raincoat that is dry. A grey folder, a white band on one wrist.",
    ),
    (
        "mr_orr",
        "character",
        "Mr. Orr",
        "Never seen. Only the plate on the door and the lamp.",
    ),
    (
        "elevator_lobby",
        "location",
        "Elevator lobby",
        "The elevator and a framed poster, five metres from the desk.",
    ),
    (
        "night_desk",
        "location",
        "The night desk",
        "The Log, the clipboard, a rotary phone with an answering machine, the printer tray and a desk drawer.",
    ),
    (
        "east_corridor",
        "location",
        "East corridor",
        "Thirty metres of grey carpet starting beside the desk.",
    ),
    (
        "east_alcove",
        "location",
        "East alcove",
        "A vending machine whose glass shows a little too much.",
    ),
    (
        "records_room",
        "location",
        "Records room",
        "Numbered filing cabinets and one old wooden drawer unit at the back.",
    ),
    (
        "cabin_approach",
        "location",
        "Outside Cabin 14",
        "The last five metres of the corridor, in front of Cabin 14.",
    ),
    (
        "cabin_14",
        "location",
        "Cabin 14",
        "Glass front, lower half frosted, a brass plate: Mr. Orr is in.",
    ),
    (
        "print_room",
        "location",
        "Print room",
        "The main printer, a supply shelf and a window onto other office towers.",
    ),
    (
        "stairwell_door",
        "location",
        "Stairwell door",
        "A badge reader, locked until 06:00.",
    ),
    (
        "the_log",
        "item",
        "The Log",
        "A ledger on the desk where visitors sign.",
    ),
    (
        "standing_instructions",
        "item",
        "Standing Instructions",
        "The rule sheet on the clipboard.",
    ),
    (
        "desk_phone",
        "item",
        "Rotary desk phone",
        "Forty line lamps and an answering machine.",
    ),
    (
        "printer_tray",
        "item",
        "Printer tray",
        "Where the count slips come out.",
    ),
)


def entity_seeds() -> list[EntitySeed]:
    return [_entity(*row) for row in ENTITY_ROWS]


def fact_seeds() -> list[FactCreate]:
    return [
        FactCreate(
            subject_entity_id=entity_id("eva_venn"),
            predicate="works_at",
            object_entity_id=entity_id("tallis_and_orr"),
        ),
        FactCreate(
            subject_entity_id=entity_id("cabin_14"),
            predicate="part_of",
            object_entity_id=entity_id("tallis_and_orr"),
        ),
        FactCreate(
            subject_entity_id=entity_id("stairwell_door"),
            predicate="locked_until",
            object_literal="06:00",
        ),
    ]
