from app.engine.alliances.answers import apply_answer
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.hashing import canonical_world_json, world_hash
from app.engine.vassals.annexation import annex_vassal
from app.engine.vassals.commands import apply_vassal_order
from app.engine.vassals.consequences import apply_reply
from app.engine.vassals.demands import resolve_demands
from app.models.orders import (
    AnnexVassalOrder,
    AnswerCallOrder,
    AnswerDemandOrder,
    DeclareWarOrder,
    DemandFromVassalOrder,
)
from app.models.world_state import WorldState
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.economy.builders import run_economy
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    add_war,
    make_demand,
    make_world,
    set_axes,
    set_power,
)

TURNS_OF_TRIBUTE = 3


def _economy_turns(world: WorldState) -> None:
    for _ in range(TURNS_OF_TRIBUTE):
        world.clock.turn += 1
        result = run_economy(world, SCENARIO)
        world.factions = result.world.factions
        world.regions = result.world.regions


def _scripted_run() -> WorldState:
    world = make_world()
    scenario = set_axes(world, SCENARIO, CAUTIOUS_RIVAL, honor=3, trust=3)
    set_power(world, CAUTIOUS_RIVAL, PLAYER, 300, 1000)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20, levy=30)
    _economy_turns(world)
    order = DemandFromVassalOrder(
        faction_id=PLAYER,
        vassalage_id=commitment.id,
        demand_kind=DemandKind.TRIBUTE,
        amount=50,
    )
    apply_vassal_order(world, scenario, order)
    world.clock.turn += scenario.tuning.vassal.demand_answer_turns
    resolve_demands(world, scenario)
    declare_war(
        world,
        scenario,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    [call] = [c for c in world.alliance.calls if c.ally_id == PLAYER]
    apply_answer(
        world,
        scenario,
        AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True),
    )
    return world


def _every_reply_world(reply: DemandReply) -> WorldState:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20)
    demand = make_demand(commitment, DemandKind.TRIBUTE, 80)
    apply_reply(world, SCENARIO, demand, reply)
    return world


def test_scripted_vassal_run_replays_with_identical_hashes() -> None:
    first, second = _scripted_run(), _scripted_run()

    assert world_hash(first) == world_hash(second)
    assert canonical_world_json(first) == canonical_world_json(second)


def test_each_demand_reply_replays_identically() -> None:
    for reply in DemandReply:
        assert world_hash(_every_reply_world(reply)) == world_hash(
            _every_reply_world(reply)
        )


def test_accept_and_refuse_leave_different_worlds() -> None:
    accepted = _every_reply_world(DemandReply.ACCEPT)
    refused = _every_reply_world(DemandReply.REFUSE)

    assert world_hash(accepted) != world_hash(refused)


def test_player_answer_is_part_of_the_hash() -> None:
    worlds = []
    for reply in (DemandReply.ACCEPT, DemandReply.REFUSE):
        world = make_world()
        add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
        apply_vassal_order(
            world,
            SCENARIO,
            DemandFromVassalOrder(
                faction_id=WRATHFUL_RIVAL,
                vassalage_id="commitment_1",
                demand_kind=DemandKind.TRIBUTE,
                amount=60,
            ),
        )
        [demand] = world.vassal.demands
        apply_vassal_order(
            world,
            SCENARIO,
            AnswerDemandOrder(faction_id=PLAYER, demand_id=demand.id, reply=reply),
        )
        worlds.append(world)

    assert world_hash(worlds[0]) != world_hash(worlds[1])


def test_annexation_run_replays_identically() -> None:
    def run() -> WorldState:
        world = make_world()
        commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
        war = add_war(world, attacker_id=PLAYER, defender_id=WRATHFUL_RIVAL)
        war.war_score_attacker = SCENARIO.tuning.vassal.annex_min_score
        world.factions[PLAYER].stability = 100
        annex_vassal(
            world,
            SCENARIO,
            AnnexVassalOrder(faction_id=PLAYER, vassalage_id=commitment.id),
        )
        return world

    assert world_hash(run()) == world_hash(run())


def test_legacy_world_dump_has_no_vassal_or_call_kind_fields() -> None:
    legacy = make_world()
    legacy.vassal_ruleset = 0
    declare_war(
        legacy,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    text = canonical_world_json(legacy)

    assert "vassal" not in text
    assert '"kind":"alliance"' not in text


def test_vassal_state_survives_a_document_round_trip() -> None:
    world = _scripted_run()

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.vassal == world.vassal


def _levy_world() -> WorldState:
    from app.models.world_army import ArmyState

    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=20)
    region_id = next(
        k for k, r in sorted(world.regions.items()) if r.owner_id == CAUTIOUS_RIVAL
    )
    world.armies = {
        "army_v": ArmyState(
            id="army_v",
            owner_id=CAUTIOUS_RIVAL,
            troops={"infantry": 100, "cavalry": 40},
            morale=50,
            location_id=region_id,
        )
    }
    apply_reply(
        world,
        SCENARIO,
        make_demand(commitment, DemandKind.LEVY, 50),
        DemandReply.ACCEPT,
    )
    return world


def test_levy_demand_taking_armies_replays_identically() -> None:
    first, second = _levy_world(), _levy_world()

    assert world_hash(first) == world_hash(second)
    assert canonical_world_json(first) == canonical_world_json(second)
