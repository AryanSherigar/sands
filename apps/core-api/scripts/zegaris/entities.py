"""World entities: locations, items, characters and organizations.

Descriptions are what a player may read. Narrator-only guidance sits in
`narrator_instruction` and never names a secret.
"""

from dataclasses import dataclass

from app.models.entity import EntityCreate
from scripts.seeding.types import EntitySeed

LOCATION = "location"
ITEM = "item"
CHARACTER = "character"
ORGANIZATION = "organization"


@dataclass(frozen=True)
class Row:
    slug: str
    kind: str
    name: str
    description: str
    aliases: tuple[str, ...] = ()
    instruction: str | None = None
    is_obtainable: bool | None = None


LOCATIONS: tuple[Row, ...] = (
    Row(
        "owls_respite",
        LOCATION,
        "Owl's Respite",
        "A wayside tavern at the high pass where the Imperial Highway splits.",
        ("the tavern", "the crossroads", "the inn", "Owl's Respite"),
        "Divided room: Zegarians in the east corner, Westerners at the hearth. "
        "Veya keeps the bar and rents beds. A bed and a hot meal for the night "
        "is the inn's rest; the game charges for it, you only describe it.",
    ),
    Row(
        "east_road",
        LOCATION,
        "The East Road",
        "A wide white-stone highway descending into a sunlit valley.",
        ("east road", "the white road"),
        "Deceptive paradise: orchards in perpetual bloom, clean streams, marble "
        "oath pillars inscribed with the First Covenant. Serfs and foreign "
        "labourers toil under the silent watch of Black Templars. Keep transit "
        "to one brisk turn and emphasise effortless beauty.",
    ),
    Row(
        "blind_shallows",
        LOCATION,
        "The Blind Shallows",
        "The muddy sprawl of tents and pens outside Zegaris' walls.",
        ("the shallows", "the camp"),
        "Outlanders, foreign merchants and labourers live here in mud, tents and "
        "livestock pens. Zegarians do not come down; they send notaries.",
    ),
    Row(
        "sunken_bazaar",
        LOCATION,
        "The Sunken Bazaar",
        "The outer market where foreign trade is allowed beyond the walls.",
        ("the bazaar", "bazaar"),
        "Zegarian notaries handle foreign goods with brass tongs and vinegar "
        "baths and never touch them. Trade is courteous and humiliating.",
    ),
    Row(
        "gate_of_the_unsworn",
        LOCATION,
        "The Gate of the Un-Sworn",
        "The gate into the Flaxen Wards, guarded by Black Templars.",
        ("the gate", "city gate"),
        "Black Templars guard it. Outsiders pass only with a worker's badge or "
        "behind a master. Show Templars as armoured and silent.",
    ),
    Row(
        "flaxen_wards",
        LOCATION,
        "The Flaxen Wards",
        "The common city: whitewashed streets, terracotta roofs, bakers and weavers.",
        ("the wards", "common city"),
        "Clean, symmetrical, genuinely warm and alive. Pale straw-yellow eyes "
        "mark common citizens. Bonded outlanders work here wearing worker "
        "badges and are ignored the way furniture is.",
    ),
    Row(
        "amber_promenade",
        LOCATION,
        "The Amber Promenade",
        "Marble avenues veined with gold, citrus courtyards and quiet canals.",
        ("the promenade", "noble terraces"),
        "Noble terraces. Outsiders are strictly forbidden unless walking behind a "
        "master. Deep honey-amber eyes. Chime-towers mark the hours.",
    ),
    Row(
        "golden_crown",
        LOCATION,
        "The Golden Crown",
        "The cathedral apex of Zegaris, guarded by White Templars.",
        ("the cathedral", "the grand cathedral"),
        "The Grand Cathedral of Zegarim, whose stained-glass icon shows an "
        "eyeless priestess calm in swallowing golden light. Molten-gold eyes. "
        "Outsiders have no business here.",
    ),
    Row(
        "swallowing_ground",
        LOCATION,
        "The Old Ground",
        "A bare stretch of mountain road above the valley, where the eclipse is watched.",
        ("the old ground", "the eclipse ground"),
        None,
    ),
    Row(
        "west_road",
        LOCATION,
        "The West Road",
        "A steep trail cut into dark shale, climbing to Ruinkrag.",
        ("west road", "the mountain trail"),
        "Biting gales with grit and freezing drizzle; the air smells of sulfur, "
        "peat smoke and wet rust; bone talismans and rusted iron scrap hang on "
        "dead pines. Keep transit to one tight turn and deliver the player to "
        "the Outer Partition.",
    ),
    Row(
        "ruinkrag_outer",
        LOCATION,
        "Ruinkrag, Outer Partition",
        "The trade and travel ring facing the mountain road.",
        ("ruinkrag", "outer partition", "sump taverns"),
        "Merchant pens, coal and iron depots, wagon stables, rough Sump Taverns. "
        "Also the evacuation route down the mountain.",
    ),
    Row(
        "council_hall",
        LOCATION,
        "The Hall of the Deep",
        "Where the Council of the Deep sits in the Iron Core.",
        ("the council", "council hall", "iron core"),
        "The military nerve centre: forges, armouries, the Great Pyres. No "
        "single person holds absolute power; speak for the Council, not a lord.",
    ),
    Row(
        "tally_gate",
        LOCATION,
        "The Tally Gate",
        "The fortified gate on the lip of the fissures, where squads are counted.",
        ("tally gate", "fissure perimeter"),
        "Every soldier is counted down and counted up. If four go down, only "
        "four may return. Trelium harpoons, murder holes, boiling pitch.",
    ),
    Row(
        "fissure_depths",
        LOCATION,
        "The Breached Shaft",
        "A deep fissure chamber where a squad was forced to retreat.",
        ("the fissure", "breached shaft", "the shaft"),
        None,
    ),
    Row(
        "great_pyres",
        LOCATION,
        "The Great Pyres",
        "The crematorium where every dead human of Ruinkrag is burned.",
        ("the pyres", "crematorium"),
        "Mandatory cremation: every dead human of Ruinkrag is incinerated.",
    ),
)

ITEMS: tuple[Row, ...] = (
    Row(
        "steel_longsword",
        ITEM,
        "Steel longsword",
        "A plain, unadorned blade.",
        (),
        None,
        True,
    ),
    Row(
        "battered_iron_armor",
        ITEM,
        "Battered iron armor",
        "Road-worn plate, dented from past battles.",
        (),
        None,
        True,
    ),
    Row(
        "forbidden_manuscript",
        ITEM,
        "The forbidden manuscript",
        "A stolen text claiming the old gods still answer prayers here.",
        (),
        None,
        True,
    ),
    Row(
        "utility_dagger",
        ITEM,
        "Utility dagger",
        "A plain working blade.",
        (),
        None,
        True,
    ),
    Row(
        "ink_and_stylus",
        ITEM,
        "Ink and brass stylus",
        "A student's ink and a brass writing stylus.",
        (),
        None,
        True,
    ),
    Row(
        "academy_robes",
        ITEM,
        "Patched academy robes",
        "Worn robes of a Grand Academy student, hidden beneath a travel cloak.",
        (),
        None,
        True,
    ),
    Row("belt_knives", ITEM, "Twin belt knives", "Quick-draw knives.", (), None, True),
    Row(
        "lockpicks", ITEM, "Concealed lockpicks", "A slim set of picks.", (), None, True
    ),
    Row("liquor_flask", ITEM, "Flask of cheap liquor", "Rough spirit.", (), None, True),
    Row(
        "leather_travel_clothes",
        ITEM,
        "Supple leather travel clothes",
        "Dark leather with hidden pockets.",
        (),
        None,
        True,
    ),
    Row("iron_mace", ITEM, "Heavy iron mace", "A priest's heavy mace.", (), None, True),
    Row(
        "prayer_stole",
        ITEM,
        "Faded prayer stole",
        "Marked with the sigil of a silent god.",
        (),
        None,
        True,
    ),
    Row(
        "silver_reliquary",
        ITEM,
        "Tarnished silver reliquary",
        "Holy embers of a dead faith.",
        (),
        None,
        True,
    ),
    Row(
        "workers_badge",
        ITEM,
        "Worker's badge",
        "A badge that lets a bonded outlander work in the Flaxen Wards.",
        ("badge",),
        None,
        True,
    ),
    Row(
        "trelium_harpoon",
        ITEM,
        "Trelium harpoon",
        "A feather-light harpoon of the only metal that harms the abominations.",
        ("harpoon",),
        None,
        True,
    ),
    Row(
        "fallen_soldiers_body",
        ITEM,
        "The fallen soldier's body",
        "What the squad left behind in the dark.",
        ("the body", "the corpse"),
        None,
        True,
    ),
)

PEOPLE: tuple[Row, ...] = (
    Row(
        "veya",
        CHARACTER,
        "Veya",
        "The tavern keeper: a woman in her thirties with a scar behind her left ear.",
        ("the barkeep", "the tavern keeper"),
        "Cynical, sharp-tongued, tired, practical. Pity is not in stock. Her "
        "leads: the east road hires foreign muscle for the Grand Tithe and pays "
        "in high coin but you must endure supreme arrogance; the west road "
        "pays bounties to clear what crawled from the fissures and half the "
        "people there sleep with a blade in hand. She does not know either "
        "city's secrets. If the player is penniless she improvises hospitality "
        "in her own way (chopping wood, a cold floor, or the door).",
    ),
    Row(
        "tithe_magistrate",
        CHARACTER,
        "The Magistrate of the Tithe",
        "A Zegarian magistrate in the east corner, recruiting outlanders.",
        ("the magistrate", "magistrate"),
        "Deep molten-gold eyes. Perfectly polite, perfectly condescending, "
        "never touches the player. Recruits newcomers with no local ties for "
        "the Grand Tithe and never says anything false.",
    ),
    Row(
        "council_captain",
        CHARACTER,
        "A captain of the Council",
        "A veteran captain who speaks for the Council of the Deep.",
        ("the captain", "captain"),
        "Scarred, blunt, shaken. Hires outlanders to recover a fallen squad "
        "member's body so the grieving squad does not have to burn their own. "
        "A newly arrived mercenary carries no risk of immediate mutation from "
        "Trelium.",
    ),
)

ORGANIZATIONS: tuple[Row, ...] = (
    Row(
        "black_templars",
        ORGANIZATION,
        "The Black Templars",
        "Armoured enforcers who deal strictly with outsiders in Zegaris.",
        ("black templar",),
        None,
    ),
    Row(
        "white_templars",
        ORGANIZATION,
        "The White Templars",
        "Armoured guardians of order among Zegarians and priests.",
        ("white templar",),
        None,
    ),
    Row(
        "council_of_the_deep",
        ORGANIZATION,
        "The Council of the Deep",
        "The shared body of captains, forge-masters and mine overseers that rules Ruinkrag.",
        ("the council",),
        None,
    ),
)


def _seed(row: Row) -> EntitySeed:
    return EntitySeed(
        row.slug,
        EntityCreate(
            entity_type=row.kind,
            canonical_name=row.name,
            aliases=list(row.aliases),
            description=row.description,
            obtainable=row.is_obtainable,
            narrator_instruction=row.instruction,
        ),
    )


def entity_seeds() -> list[EntitySeed]:
    rows = (*LOCATIONS, *ITEMS, *PEOPLE, *ORGANIZATIONS)
    return [_seed(row) for row in rows]


LOCATION_SLUGS = tuple(row.slug for row in LOCATIONS)
ITEM_SLUGS = tuple(row.slug for row in ITEMS)
