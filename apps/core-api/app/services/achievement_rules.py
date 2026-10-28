"""Pure achievement rules: metrics in, (current, target) progress out."""

from dataclasses import dataclass

from app.services.achievement_catalogue import (
    ACHIEVEMENT_CATALOGUE,
    EVERY_ENDING_KEY,
    AchievementDefinition,
)

EMPTY_EVERY_ENDING_PROGRESS = (0, 1)


@dataclass(frozen=True)
class AchievementMetrics:
    turns_taken: int = 0
    stories_completed: int = 0
    wins: int = 0
    endings_found: int = 0
    worlds_played: int = 0
    genres_played: int = 0
    canonical_genres_played: int = 0
    best_story_found: int = 0
    best_story_total: int = 0
    published_count: int = 0
    plays_received: int = 0
    five_star_reviews: int = 0


def _every_ending_progress(metrics: AchievementMetrics) -> tuple[int, int]:
    if metrics.best_story_total <= 0:
        return EMPTY_EVERY_ENDING_PROGRESS
    found = min(metrics.best_story_found, metrics.best_story_total)
    return found, metrics.best_story_total


def _progress(
    definition: AchievementDefinition, metrics: AchievementMetrics
) -> tuple[int, int]:
    if definition.key == EVERY_ENDING_KEY:
        return _every_ending_progress(metrics)
    current = int(getattr(metrics, definition.metric))
    return min(current, definition.target), definition.target


def compute_progress(metrics: AchievementMetrics) -> dict[str, tuple[int, int]]:
    return {d.key: _progress(d, metrics) for d in ACHIEVEMENT_CATALOGUE}


def earned_keys(progress: dict[str, tuple[int, int]]) -> list[str]:
    return [
        d.key for d in ACHIEVEMENT_CATALOGUE if progress[d.key][0] >= progress[d.key][1]
    ]


def pick_best_story(stories: list[tuple[int, int]]) -> tuple[int, int]:
    counted = [(found, total) for found, total in stories if total > 0]
    if not counted:
        return 0, 0
    return max(counted, key=lambda pair: (pair[0] / pair[1], pair[1]))
