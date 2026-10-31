from app.engine.stances.menu import resolve_stance_menu
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import BUILTIN_STANCES

CUSTOM = {"id": "reclaim_marches", "name": "Reclaim", "shifts": {"attack": 2}}
FACTION = {"id": "house_ashford", "name": "Ashford", "color": "#aabbcc"}


def _scenario(stance_ids: list[str] | None = None) -> StrategyScenario:
    faction = FACTION | ({"stance_ids": stance_ids} if stance_ids is not None else {})
    return StrategyScenario.model_validate(
        {"custom_stances": [CUSTOM], "factions": [faction]}
    )


def test_menu_is_sorted_and_includes_custom() -> None:
    menu = resolve_stance_menu(_scenario(), "house_ashford")
    ids = [stance.id for stance in menu]
    assert ids == sorted(ids)
    assert "reclaim_marches" in ids
    assert {stance.id for stance in BUILTIN_STANCES} <= set(ids)


def test_faction_stance_ids_restrict_menu() -> None:
    menu = resolve_stance_menu(
        _scenario(["turtle", "reclaim_marches"]), "house_ashford"
    )
    assert [stance.id for stance in menu] == ["reclaim_marches", "turtle"]


def test_unlisted_faction_gets_the_full_menu() -> None:
    menu = resolve_stance_menu(_scenario(["turtle"]), "house_carrow")
    assert len(menu) == len(BUILTIN_STANCES) + 1


def test_menu_is_identical_across_calls() -> None:
    scenario = _scenario()
    first = resolve_stance_menu(scenario, "house_ashford")
    second = resolve_stance_menu(scenario, "house_ashford")
    assert first == second
