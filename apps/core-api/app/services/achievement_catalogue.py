"""The fixed v1 achievement catalogue: names, requirements and thresholds."""

from dataclasses import dataclass

# NOTE: mirrors apps/frontend/src/shared/constants/genres.ts GENRES, because
# genre_tags are free text in the API and "all genres" needs a fixed list.
CANONICAL_GENRES: tuple[str, ...] = (
    "High Fantasy",
    "Sci-Fi",
    "Adventure/Survival",
    "Slice of Life",
    "Noir / Detective",
    "Post-Apocalyptic/Dystopian",
    "Cyberpunk",
    "Horror",
    "Historical Fiction",
    "Mystery",
)

FAMILY_JOURNEY = "Journey"
FAMILY_EXPLORER = "Explorer"
FAMILY_COMPLETIONIST = "Completionist"
FAMILY_CREATOR = "Creator"
EVERY_ENDING_KEY = "every-ending"


@dataclass(frozen=True)
class AchievementDefinition:
    key: str
    name: str
    family: str
    requirement: str
    metric: str
    target: int


ACHIEVEMENT_CATALOGUE: tuple[AchievementDefinition, ...] = (
    AchievementDefinition(
        "first-steps",
        "First Steps",
        FAMILY_JOURNEY,
        "Take your first turn",
        "turns_taken",
        1,
    ),
    AchievementDefinition(
        "final-page",
        "Final Page",
        FAMILY_JOURNEY,
        "Conclude or finish your first story",
        "stories_completed",
        1,
    ),
    AchievementDefinition(
        "wayfarer",
        "Wayfarer",
        FAMILY_JOURNEY,
        "Take 100 turns",
        "turns_taken",
        100,
    ),
    AchievementDefinition(
        "voyager",
        "Voyager",
        FAMILY_JOURNEY,
        "Take 500 turns",
        "turns_taken",
        500,
    ),
    AchievementDefinition(
        "chronicler",
        "Chronicler",
        FAMILY_JOURNEY,
        "Take 1,000 turns",
        "turns_taken",
        1000,
    ),
    AchievementDefinition(
        "genre-curious",
        "Genre Curious",
        FAMILY_EXPLORER,
        "Play stories in 3 different genres",
        "genres_played",
        3,
    ),
    AchievementDefinition(
        "every-shelf",
        "Every Shelf",
        FAMILY_EXPLORER,
        "Play stories in all genres",
        "canonical_genres_played",
        len(CANONICAL_GENRES),
    ),
    AchievementDefinition(
        "five-worlds",
        "Five Worlds",
        FAMILY_EXPLORER,
        "Play 5 different stories",
        "worlds_played",
        5,
    ),
    AchievementDefinition(
        "far-traveller",
        "Far Traveller",
        FAMILY_EXPLORER,
        "Play 25 different stories",
        "worlds_played",
        25,
    ),
    AchievementDefinition(
        "an-ending",
        "An Ending",
        FAMILY_COMPLETIONIST,
        "Reach any author-defined ending",
        "endings_found",
        1,
    ),
    AchievementDefinition(
        "triumph",
        "Triumph",
        FAMILY_COMPLETIONIST,
        "Reach a winning ending",
        "wins",
        1,
    ),
    AchievementDefinition(
        EVERY_ENDING_KEY,
        "Every Ending",
        FAMILY_COMPLETIONIST,
        "Find all endings of one story",
        "best_story_found",
        1,
    ),
    AchievementDefinition(
        "worldmaker",
        "Worldmaker",
        FAMILY_CREATOR,
        "Publish your first story",
        "published_count",
        1,
    ),
    AchievementDefinition(
        "first-readers",
        "First Readers",
        FAMILY_CREATOR,
        "Your stories reach 10 plays",
        "plays_received",
        10,
    ),
    AchievementDefinition(
        "crowd",
        "Crowd",
        FAMILY_CREATOR,
        "Your stories reach 100 plays",
        "plays_received",
        100,
    ),
    AchievementDefinition(
        "beloved",
        "Beloved",
        FAMILY_CREATOR,
        "Your stories reach 1,000 plays",
        "plays_received",
        1000,
    ),
    AchievementDefinition(
        "five-stars",
        "Five Stars",
        FAMILY_CREATOR,
        "Receive your first 5-star review",
        "five_star_reviews",
        1,
    ),
)

_BY_KEY = {definition.key: definition for definition in ACHIEVEMENT_CATALOGUE}
_INDEX_BY_KEY = {d.key: index for index, d in enumerate(ACHIEVEMENT_CATALOGUE)}


def get_definition(key: str) -> AchievementDefinition | None:
    return _BY_KEY.get(key)


def get_catalogue_index(key: str) -> int:
    return _INDEX_BY_KEY[key]
