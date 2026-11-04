from app.services.achievement_catalogue import (
    ACHIEVEMENT_CATALOGUE,
    CANONICAL_GENRES,
    get_catalogue_index,
    get_definition,
)
from app.services.achievement_rules import (
    AchievementMetrics,
    compute_progress,
    earned_keys,
    pick_best_story,
)


def test_catalogue_has_17_unique_keys_in_four_families() -> None:
    keys = [d.key for d in ACHIEVEMENT_CATALOGUE]
    assert len(keys) == len(set(keys)) == 17
    families = [d.family for d in ACHIEVEMENT_CATALOGUE]
    counts = [
        families.count(f) for f in ("Journey", "Explorer", "Completionist", "Creator")
    ]
    assert counts == [5, 4, 3, 5]


def test_catalogue_uses_the_specified_names_and_requirements() -> None:
    wayfarer = get_definition("wayfarer")
    assert wayfarer is not None
    assert (wayfarer.name, wayfarer.requirement) == ("Wayfarer", "Take 100 turns")
    chronicler = get_definition("chronicler")
    assert chronicler is not None
    assert chronicler.requirement == "Take 1,000 turns"
    assert get_definition("nope") is None
    assert get_catalogue_index("first-steps") == 0
    assert get_catalogue_index("five-stars") == 16


def test_ten_canonical_genres() -> None:
    assert len(CANONICAL_GENRES) == 10
    assert "Noir / Detective" in CANONICAL_GENRES


def test_empty_metrics_earn_nothing_and_show_zero_progress() -> None:
    progress = compute_progress(AchievementMetrics())
    assert earned_keys(progress) == []
    assert progress["wayfarer"] == (0, 100)
    assert progress["every-ending"] == (0, 1)
    assert progress["every-shelf"] == (0, 10)


def test_turn_thresholds_at_the_boundary() -> None:
    at_99 = earned_keys(compute_progress(AchievementMetrics(turns_taken=99)))
    assert "wayfarer" not in at_99
    at_100 = earned_keys(compute_progress(AchievementMetrics(turns_taken=100)))
    assert "wayfarer" in at_100
    at_999 = earned_keys(compute_progress(AchievementMetrics(turns_taken=999)))
    assert "voyager" in at_999 and "chronicler" not in at_999
    at_1000 = set(earned_keys(compute_progress(AchievementMetrics(turns_taken=1000))))
    assert {"first-steps", "wayfarer", "voyager", "chronicler"} <= at_1000


def test_progress_is_capped_at_target() -> None:
    progress = compute_progress(AchievementMetrics(turns_taken=5000))
    assert progress["wayfarer"] == (100, 100)


def test_explorer_and_creator_thresholds() -> None:
    metrics = AchievementMetrics(
        genres_played=3,
        canonical_genres_played=10,
        worlds_played=25,
        published_count=1,
        plays_received=10,
        five_star_reviews=1,
    )
    earned = set(earned_keys(compute_progress(metrics)))
    assert {
        "genre-curious",
        "every-shelf",
        "five-worlds",
        "far-traveller",
        "worldmaker",
        "first-readers",
        "five-stars",
    } <= earned
    assert "crowd" not in earned


def test_completionist_badges() -> None:
    earned = set(
        earned_keys(compute_progress(AchievementMetrics(endings_found=1, wins=0)))
    )
    assert "an-ending" in earned and "triumph" not in earned
    with_win = earned_keys(
        compute_progress(AchievementMetrics(endings_found=1, wins=1))
    )
    assert "triumph" in with_win


def test_every_ending_needs_a_complete_story() -> None:
    partial = compute_progress(
        AchievementMetrics(best_story_found=2, best_story_total=3)
    )
    assert partial["every-ending"] == (2, 3)
    assert "every-ending" not in earned_keys(partial)
    complete = compute_progress(
        AchievementMetrics(best_story_found=3, best_story_total=3)
    )
    assert "every-ending" in earned_keys(complete)
    none = compute_progress(AchievementMetrics(best_story_found=0, best_story_total=0))
    assert "every-ending" not in earned_keys(none)


def test_pick_best_story() -> None:
    assert pick_best_story([]) == (0, 0)
    assert pick_best_story([(0, 0)]) == (0, 0)
    assert pick_best_story([(1, 4), (2, 3)]) == (2, 3)
    assert pick_best_story([(2, 4), (3, 6)]) == (3, 6)  # tie on ratio -> larger total
