"""The 28 location entities. Names follow the canon geography (Missian Province,
Canare, Lamberk, Torbekistan, Kumeil, Semplar); every interior place and its
description is this scenario's own arrangement, flagged for the owner's review.
"""

from dataclasses import dataclass

from app.models.entity import EntityCreate
from scripts.seeding.types import EntitySeed

LOCATION_TYPE = "location"


@dataclass(frozen=True)
class LocationSpec:
    slug: str
    name: str
    description: str
    aliases: tuple[str, ...] = ()


REGIONS: tuple[LocationSpec, ...] = (
    LocationSpec(
        "lamberk_region",
        "Lamberk",
        "A small valley territory ruled by House Louvent.",
        ("the valley", "the territory", "home"),
    ),
    LocationSpec(
        "canare_region",
        "Canare",
        "The county around Lamberk. Its castle town is the seat of the county chief.",
        ("Canare County", "Canare Town"),
    ),
    LocationSpec(
        "torbekistan_region",
        "Torbekistan",
        "A neighbouring territory in Canare, held by House Plaid.",
        ("Plaid lands",),
    ),
    LocationSpec(
        "kumeil_region",
        "Kumeil",
        "A modest territory on the road between Lamberk and Torbekistan.",
    ),
    LocationSpec(
        "semplar_region",
        "Semplar",
        "A busy trading port on the southern coast, far from home.",
        ("the port",),
    ),
)

MANOR: tuple[LocationSpec, ...] = (
    LocationSpec(
        "manor_gate",
        "Louvent Manor gate",
        "The gate and yard of the modest manor that House Louvent calls home.",
        ("the gate", "the manor", "the courtyard"),
    ),
    LocationSpec(
        "manor_hall",
        "The manor hall",
        "A plain, warm hall where the family eats and the household gathers.",
        ("the hall",),
    ),
    LocationSpec(
        "ars_room",
        "Ars's room",
        "A child's room with a narrow bed, a small desk and a window onto the valley.",
        ("my room", "the bedroom"),
    ),
    LocationSpec(
        "raven_chamber",
        "Raven's chamber",
        "The lord's chamber, quiet and kept warm.",
        ("father's room", "Raven's room"),
    ),
    LocationSpec(
        "manor_study",
        "The study",
        "Ledgers, maps and a table scarred by years of lessons.",
        ("the library", "the ledgers"),
    ),
    LocationSpec(
        "manor_kitchen",
        "The kitchen",
        "Steam, bread and the household's gossip.",
        ("the kitchens",),
    ),
)

TOWN: tuple[LocationSpec, ...] = (
    LocationSpec(
        "town_square",
        "Lamberk market square",
        "The heart of Lamberk town: stalls, carts and neighbours trading news.",
        ("the market", "the square", "town"),
    ),
    LocationSpec(
        "slave_quarter",
        "The slave traders' quarter",
        "A grim row of pens and cages at the edge of town where people are sold.",
        ("the traders", "the slave market"),
    ),
    LocationSpec(
        "town_inn",
        "The Lamberk inn",
        "A low-beamed inn where travellers swap stories and rumours.",
        ("the inn", "the tavern"),
    ),
    LocationSpec(
        "smithy",
        "The smithy",
        "The smith's forge, loud with hammering and the smell of hot iron.",
        ("the forge", "the smith"),
    ),
)

SHADOWS: tuple[LocationSpec, ...] = (
    LocationSpec(
        "shadow_tavern",
        "The Shadows' tavern",
        "A dim tavern in a back street where nobody asks who you are.",
        ("the back-street tavern",),
    ),
    LocationSpec(
        "shadow_backroom",
        "The tavern back room",
        "A cramped room behind the bar where the Shadows do their business.",
        ("the back room",),
    ),
)

TRAINING: tuple[LocationSpec, ...] = (
    LocationSpec(
        "sparring_yard",
        "The sparring yard",
        "Packed earth and wooden practice swords, where Lamberk's soldiers drill.",
        ("the training grounds", "the practice yard"),
    ),
    LocationSpec(
        "archery_range",
        "The archery range",
        "A long strip of grass with straw targets at the far end.",
        ("the range",),
    ),
    LocationSpec(
        "barracks",
        "The barracks",
        "Bunks, racks of spears and the smell of boiled cabbage.",
        ("the soldiers' quarters",),
    ),
)

FARMLAND: tuple[LocationSpec, ...] = (
    LocationSpec(
        "farm_village",
        "The village",
        "A cluster of farmers' houses around a well.",
        ("the villages", "the farms"),
    ),
    LocationSpec(
        "wheat_fields",
        "The wheat fields",
        "Rolling fields that feed the valley, or fail to.",
        ("the fields",),
    ),
    LocationSpec(
        "mill",
        "The river mill",
        "A water mill on the stream that cuts through the valley.",
        ("the watermill",),
    ),
)

CANARE: tuple[LocationSpec, ...] = (
    LocationSpec(
        "canare_gate",
        "Canare Castle gate",
        "The stone gatehouse of the county seat.",
        ("the castle", "Canare Castle"),
    ),
    LocationSpec(
        "canare_hall",
        "The Canare great hall",
        "A high hall where the county chief receives guests.",
        ("the great hall",),
    ),
    LocationSpec(
        "canare_council",
        "The council room",
        "A long table, a map and a lot of careful manners.",
        ("the council",),
    ),
)

PLAID: tuple[LocationSpec, ...] = (
    LocationSpec(
        "plaid_house",
        "The Plaid manor",
        "A tidy, well-kept house, richer than Louvent Manor.",
        ("the Plaid house",),
    ),
    LocationSpec(
        "plaid_garden",
        "The Plaid garden",
        "A walled garden where Lysia likes to think.",
        ("the garden",),
    ),
)

LOCATION_GROUPS = (REGIONS, MANOR, TOWN, SHADOWS, TRAINING, FARMLAND, CANARE, PLAID)
LOCATIONS: tuple[LocationSpec, ...] = tuple(
    spec for group in LOCATION_GROUPS for spec in group
)
LOCATION_SLUGS = tuple(spec.slug for spec in LOCATIONS)


def location_seed(spec: LocationSpec) -> EntitySeed:
    return EntitySeed(
        spec.slug,
        EntityCreate(
            entity_type=LOCATION_TYPE,
            canonical_name=spec.name,
            aliases=list(spec.aliases),
            description=spec.description,
        ),
    )


def location_seeds() -> list[EntitySeed]:
    return [location_seed(spec) for spec in LOCATIONS]
