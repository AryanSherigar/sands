from app.models.world_diplomacy import AgentState, EnvoyState
from app.models.world_pressure import RumorState
from app.services.world_projection import project_world
from strategy_contracts.agents import AgentTrait
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.engine.pressure.test_effects import _exhaust

VERSION = 1
DIGEST = "digest"
FORBIDDEN_KEYS = {
    "pressure",
    "last_bands",
    "shocks",
    "humiliation",
    "devastation",
    "mediation_offers",
    "stalemate_turns",
    "is_hint_wrong",
    "hope",
    "floor",
}
OWN_PRESSURE_KEYS = {
    "will_band",
    "strain_band",
    "will_factors",
    "strain_factors",
}
RUMOR_KEYS = {"about_faction_id", "topic", "band", "line_key", "turn"}


def _war_world():
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    set_traits(world, PLAYER, ["pragmatic"])
    return world


def _view(world):
    return project_world(world, SCENARIO, VERSION, DIGEST)


def _all_keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _all_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _all_keys(v)}
    return set()


def test_view_contains_own_bands_and_factors() -> None:
    world = _war_world()
    _exhaust(world, PLAYER)

    view = _view(world)

    assert view.own_pressure is not None
    assert set(view.own_pressure.model_dump()) == OWN_PRESSURE_KEYS
    assert view.own_pressure.strain_band in (PressureBand.HIGH, PressureBand.VERY_HIGH)
    assert "devastation" in view.own_pressure.strain_factors


def test_view_has_no_pressure_for_a_faction_at_peace() -> None:
    view = _view(make_world())

    assert view.own_pressure is None
    assert view.rumors == []


def test_legacy_world_view_has_no_pressure() -> None:
    world = _war_world()
    world.pressure_ruleset = 0

    assert _view(world).own_pressure is None


def test_view_never_contains_rival_numeric_will_or_strain() -> None:
    world = _war_world()
    _exhaust(world, WRATHFUL_RIVAL)

    dumped = _view(world).model_dump()

    assert "will" not in dumped and "strain" not in dumped
    rivals = {rival["faction_id"]: rival for rival in dumped["rivals"]}
    assert set(rivals[WRATHFUL_RIVAL]) == {
        "faction_id",
        "name",
        "leader_name",
        "relation",
        "treasury_range",
        "manpower_range",
    }


def test_view_never_contains_hope_sources_shocks_or_humiliation() -> None:
    world = _war_world()
    world.pressure.humiliation[PLAYER] = 20
    world.pressure.devastation["brennmoor"] = 40
    world.pressure.last_bands[PLAYER] = "low:low"

    dumped = _view(world).model_dump()
    for own_factors in ("will_factors", "strain_factors"):
        dumped["own_pressure"].pop(own_factors)

    assert not (_all_keys(dumped) & FORBIDDEN_KEYS)


def test_only_the_players_own_rumors_are_projected_without_numbers() -> None:
    world = _war_world()
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=WRATHFUL_RIVAL)
    )
    for index, observer in enumerate((PLAYER, CAUTIOUS_RIVAL), start=1):
        world.pressure.rumors.append(
            RumorState(
                id=f"rumor_{index}",
                observer_id=observer,
                about_faction_id=WRATHFUL_RIVAL,
                envoy_id="envoy_1",
                topic=RumorTopic.WILL,
                band=PressureBand.HIGH,
                line_key="will.high",
                turn=world.clock.turn,
                is_hint_wrong=True,
            )
        )

    rumors = _view(world).model_dump()["rumors"]

    assert len(rumors) == 1
    assert set(rumors[0]) == RUMOR_KEYS
    assert [
        v for v in rumors[0].values() if isinstance(v, int) and v != world.clock.turn
    ] == []


def test_view_exposes_no_agent_internals() -> None:
    world = _war_world()
    _exhaust(world, WRATHFUL_RIVAL)
    world.envoys.append(
        EnvoyState(
            id="envoy_1",
            from_faction_id=PLAYER,
            at_faction_id=WRATHFUL_RIVAL,
            agent=AgentState(
                name="Aldous",
                traits=[AgentTrait.PIOUS],
                loyalty=77,
                bribed_by=WRATHFUL_RIVAL,
            ),
        )
    )

    dumped = _view(world).model_dump(mode="json")

    assert not {"agent", "bribed_by", "loyalty", "is_hint_wrong"} & _all_keys(dumped)
    assert "Aldous" not in str(dumped)
