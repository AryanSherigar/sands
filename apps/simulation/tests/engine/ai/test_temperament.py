from app.engine.ai.temperament import temperament_bias
from strategy_contracts.stances import ScoreCategory

SEED = 20261027


def test_bias_is_bounded_and_stable() -> None:
    for index in range(50):
        for category in ScoreCategory:
            bias = temperament_bias(SEED, f"leader_{index}", category)
            assert -2 <= bias <= 2
            assert bias == temperament_bias(SEED, f"leader_{index}", category)


def test_bias_differs_between_leaders_and_categories() -> None:
    by_leader = {
        temperament_bias(SEED, f"leader_{index}", ScoreCategory.ATTACK)
        for index in range(30)
    }
    by_category = {
        temperament_bias(SEED, "mira", category) for category in ScoreCategory
    }

    assert len(by_leader) > 1
    assert len(by_category) > 1


def test_bias_depends_on_the_playthrough_seed() -> None:
    first = [temperament_bias(1, "mira", category) for category in ScoreCategory]
    second = [temperament_bias(2, "mira", category) for category in ScoreCategory]

    assert first != second
