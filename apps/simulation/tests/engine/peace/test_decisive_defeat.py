from app.engine.diplomacy.phase import TimePhase
from app.engine.peace.decisive_defeat import apply_decisive_defeats
from app.models.world_battle import (
    BattleContingent,
    BattleSide,
    BattleState,
    BattleStatus,
)
from app.models.world_state import WorldState
from strategy_contracts.enums import TroopType

from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_score,
    set_war_relation,
)

TUNING = SCENARIO.tuning.peace
ENTRY_TROOPS = 260


def _shrink_player_armies(world: WorldState, total: int) -> None:
    armies = [army for army in world.armies.values() if army.owner_id == PLAYER]
    for army in armies:
        army.troops = {}
    armies[0].troops = {TroopType.INFANTRY: total}


def _record_decisive_battle(world: WorldState, war_id: str) -> None:
    contingent = BattleContingent(
        faction_id=PLAYER,
        side=BattleSide.DEFENDER,
        army_ids=[],
        entry_troops=ENTRY_TROOPS,
    )
    world.battles.append(
        BattleState(
            id="battle_1",
            region_id=region_of(world, PLAYER),
            attacker_army_ids=[],
            defender_army_ids=[],
            status=BattleStatus.RESOLVED,
            contingents={PLAYER: contingent},
        )
    )
    next(war for war in world.wars if war.id == war_id).scored_battle_ids = ["battle_1"]


def region_of(world: WorldState, faction_id: str) -> str:
    return next(
        key
        for key, region in sorted(world.regions.items())
        if region.owner_id == faction_id
    )


def _beaten_world(lead: int, troops: int) -> WorldState:
    world = make_world()
    world.defeat_ruleset = 1
    set_war_relation(world, PLAYER, WRATHFUL_RIVAL)
    war = add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    set_score(war, attacker=lead, defender=0)
    war.battle_points_attacker = lead
    _shrink_player_armies(world, troops)
    _record_decisive_battle(world, war.id)
    return world


def test_decisive_defeat_ends_war_and_cedes_one_region() -> None:
    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead, troops=69)
    regions_before = sum(1 for r in world.regions.values() if r.owner_id == PLAYER)

    events = apply_decisive_defeats(world, SCENARIO)

    regions_after = sum(1 for r in world.regions.values() if r.owner_id == PLAYER)
    assert world.wars == []
    assert regions_after == regions_before - 1
    assert [event.kind for event in events][-1] == "decisive_defeat"
    assert world.truces[0].loser_id == PLAYER


def test_no_defeat_when_the_score_lead_is_below_the_threshold() -> None:
    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead - 1, troops=69)
    assert apply_decisive_defeats(world, SCENARIO) == []
    assert len(world.wars) == 1


def test_no_defeat_while_the_loser_still_has_most_of_its_host() -> None:
    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead, troops=200)
    assert apply_decisive_defeats(world, SCENARIO) == []
    assert len(world.wars) == 1


def test_no_defeat_without_the_ruleset() -> None:
    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead, troops=69)
    world.defeat_ruleset = 0
    assert apply_decisive_defeats(world, SCENARIO) == []
    assert len(world.wars) == 1


def test_no_defeat_without_a_recorded_battle_baseline() -> None:
    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead, troops=69)
    world.wars[0].scored_battle_ids = []
    assert apply_decisive_defeats(world, SCENARIO) == []


def test_time_phase_applies_a_decisive_defeat() -> None:
    from tests.engine.diplomacy.builders import run_phase

    world = _beaten_world(lead=TUNING.decisive_defeat_score_lead, troops=69)

    result = run_phase(TimePhase(), world)

    assert result.world.wars == []
    assert "decisive_defeat" in [event.kind for event in result.events]
