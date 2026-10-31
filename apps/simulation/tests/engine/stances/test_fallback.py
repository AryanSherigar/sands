from app.engine.stances.fallback import fallback_stance_id
from app.engine.stances.menu import resolve_stance_menu
from app.models.world_character import LeaderState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory, StanceDefinition
from strategy_contracts.traits import TraitAxis, TraitDefinition

SCENARIO = StrategyScenario(
    custom_traits=[
        TraitDefinition(
            id="warlike", name="Warlike", effects={TraitAxis.AGGRESSION: 3}
        ),
        TraitDefinition(id="wary", name="Wary", effects={TraitAxis.CAUTION: 3}),
    ]
)


def _leader(trait_ids: list[str]) -> LeaderState:
    return LeaderState(
        id="mira", name="Mira", faction_id="house_ashford", age=40, trait_ids=trait_ids
    )


def test_aggressive_leader_prefers_attack_leaning_stance() -> None:
    menu = resolve_stance_menu(SCENARIO, "house_ashford")
    assert fallback_stance_id(_leader(["warlike"]), menu, SCENARIO) == "expand"


def test_cautious_leader_prefers_rebuilding() -> None:
    menu = resolve_stance_menu(SCENARIO, "house_ashford")
    assert fallback_stance_id(_leader(["wary"]), menu, SCENARIO) == "rebuild"


def test_tie_breaks_by_menu_order() -> None:
    shifts = {ScoreCategory.BUILD: 1}
    menu = [
        StanceDefinition(id="first_pick", name="A", shifts=shifts),
        StanceDefinition(id="second_pick", name="B", shifts=shifts),
    ]
    assert fallback_stance_id(_leader(["warlike"]), menu, SCENARIO) == "first_pick"


def test_single_stance_menu_returns_it() -> None:
    menu = [StanceDefinition(id="only_one", name="Only", shifts={})]
    assert fallback_stance_id(_leader([]), menu, SCENARIO) == "only_one"


def test_unknown_trait_ids_are_ignored() -> None:
    menu = resolve_stance_menu(SCENARIO, "house_ashford")
    assert fallback_stance_id(_leader(["not_a_trait"]), menu, SCENARIO) in {
        stance.id for stance in menu
    }
