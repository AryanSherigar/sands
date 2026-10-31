from app.engine.ai.catalog import GENERATORS, legal_candidates
from app.engine.ai.generators.espionage import bribe_candidates
from app.engine.pressure.agents import bribe_price
from app.models.orders import BribeEnvoyOrder
from app.models.world_ai import AimState
from app.models.world_diplomacy import AgentState, EnvoyState
from strategy_contracts.agents import AgentTrait
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.engine.pressure.builders import (
    SCENARIO as BASE_SCENARIO,
)

LOYALTY = 50
HOST = WRATHFUL_RIVAL
RICH = 5000


def _scenario(is_enabled: bool = True):
    scenario = BASE_SCENARIO.model_copy(deep=True)
    scenario.tuning.agents.is_enabled = is_enabled
    return scenario


def _world(*, sender: str = PLAYER, at: str = HOST, bribed_by=None):
    world = make_world()
    world.envoys.append(
        EnvoyState(
            id="envoy_1",
            from_faction_id=sender,
            at_faction_id=at,
            agent=AgentState(
                name="Aldous",
                traits=[AgentTrait.HONEST],
                loyalty=LOYALTY,
                bribed_by=bribed_by,
            ),
        )
    )
    world.factions[HOST].treasury = RICH
    return world


def _make_hostile(world, sender: str = PLAYER) -> None:
    add_war(world, attacker_id=HOST, defender_id=sender)


def test_hostile_rival_plans_bribe_for_foreign_envoy_in_its_court() -> None:
    world = _world()
    _make_hostile(world)
    scenario = _scenario()

    found = bribe_candidates(world, scenario, HOST)

    assert [c.order for c in found] == [
        BribeEnvoyOrder(faction_id=HOST, envoy_id="envoy_1")
    ]
    assert found[0].category is ScoreCategory.ATTACK


def test_aim_target_counts_as_hostile() -> None:
    world = _world()
    world.aims[HOST] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=PLAYER,
        chosen_turn=0,
        leader_id=world.factions[HOST].leader_id,
        capital_held=True,
    )

    assert bribe_candidates(world, _scenario(), HOST)


def test_no_bribe_for_non_hostile_sender() -> None:
    assert bribe_candidates(_world(), _scenario(), HOST) == []


def test_no_bribe_when_it_would_drop_below_low_treasury() -> None:
    world = _world()
    _make_hostile(world)
    scenario = _scenario()
    price = bribe_price(world.envoys[0].agent, scenario.tuning.agents)
    world.factions[HOST].treasury = price + scenario.tuning.ai.low_treasury - 1

    assert bribe_candidates(world, scenario, HOST) == []


def test_no_bribe_of_already_bribed_agent() -> None:
    world = _world(bribed_by=CAUTIOUS_RIVAL)
    _make_hostile(world)

    assert bribe_candidates(world, _scenario(), HOST) == []


def test_no_bribe_when_agents_disabled() -> None:
    world = _world()
    _make_hostile(world)

    assert bribe_candidates(world, _scenario(is_enabled=False), HOST) == []


def test_generator_ignores_envoys_posted_in_other_courts() -> None:
    world = _world(at=CAUTIOUS_RIVAL)
    _make_hostile(world)

    assert bribe_candidates(world, _scenario(), HOST) == []


def test_cunning_ruler_scores_the_bribe_higher() -> None:
    world = _world()
    _make_hostile(world)
    scenario = _scenario()
    set_traits(world, HOST, [])
    plain = bribe_candidates(world, scenario, HOST)[0].base_score
    set_traits(world, HOST, ["cunning"])

    cunning = bribe_candidates(world, scenario, HOST)[0].base_score

    assert plain == scenario.tuning.agents.bribe_score_bonus
    assert cunning > plain


def test_bribe_candidates_pass_check_command() -> None:
    world = _world()
    _make_hostile(world)
    scenario = _scenario()
    found = bribe_candidates(world, scenario, HOST)

    assert legal_candidates(world, scenario, HOST, found) == found


def test_generator_is_registered_in_the_catalog() -> None:
    assert bribe_candidates in GENERATORS
