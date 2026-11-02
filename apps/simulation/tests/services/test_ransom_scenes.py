from app.engine.diplomacy.prisoners import handle_prisoner
from app.engine.negotiation_triggers import arm_triggered_negotiation
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.repositories import scene_exchange_repo, scene_repo
from app.services.triggered_negotiation import persist_triggered_scene
from strategy_contracts.enums import TroopType
from strategy_contracts.scene import (
    SceneInitiator,
    SceneType,
    TermsCardOutcome,
    TermsResult,
)
from strategy_contracts.scene_validation import validate_outcome_against_package
from strategy_contracts.terms import ReleasePrisonersTerm
from tests.engine.overtures.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough

HOLDER = WRATHFUL_RIVAL
RICH = 100000


def _captive(world, holder: str, origin: str, prisoner_id: str = "prisoner_1"):
    world.prisoners.append(
        PrisonerState(
            id=prisoner_id,
            held_by_id=holder,
            origin_faction_id=origin,
            kind=PrisonerKind.TROOPS,
            troop_count=100,
            origin_battle_id="battle_1",
            troops_by_type={TroopType.INFANTRY: 100},
        )
    )


def _demand_world():
    world = make_world()
    world.playthrough_id = PLAYTHROUGH_ID
    world.factions[PLAYER].treasury = RICH
    _captive(world, HOLDER, PLAYER)
    arm_triggered_negotiation(world, SCENARIO)
    return world


def _counter_world():
    world = make_world()
    world.playthrough_id = PLAYTHROUGH_ID
    world.factions[WRATHFUL_RIVAL].treasury = RICH
    world.factions[WRATHFUL_RIVAL].stability = 100
    _captive(world, PLAYER, WRATHFUL_RIVAL)
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action="ransom"
    )
    handle_prisoner(world, SCENARIO, order)
    arm_triggered_negotiation(world, SCENARIO)
    return world


async def test_ransom_demand_persists_an_npc_scene_with_the_ransom_proposed(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = _demand_world()

    await persist_triggered_scene(db_connection, world, SCENARIO)

    scene_id = world.progress.pending_scene_id
    scene = await scene_repo.get_scene(db_connection, scene_id)
    assert scene.package.initiator is SceneInitiator.AI
    assert scene.package.is_declinable is True
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert len(exchanges) == 1
    term = exchanges[0].proposal.terms[0]
    assert isinstance(term, ReleasePrisonersTerm)
    assert term.holder_id == HOLDER
    assert exchanges[0].leader_text == (
        world.progress.pending_negotiation.overture.pretext
    )


async def test_ransom_counter_persists_a_scene_proposing_the_npcs_price(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = _counter_world()
    gold = world.progress.pending_negotiation.overture.card.terms[0].ransom_gold

    await persist_triggered_scene(db_connection, world, SCENARIO)

    scene_id = world.progress.pending_scene_id
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    term = exchanges[0].proposal.terms[0]
    assert isinstance(term, ReleasePrisonersTerm)
    assert (term.holder_id, term.recipient_id) == (PLAYER, WRATHFUL_RIVAL)
    assert term.ransom_gold == gold


async def test_the_stored_scene_accepts_the_ransom_card_as_a_valid_outcome(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = _demand_world()
    await persist_triggered_scene(db_connection, world, SCENARIO)
    scene = await scene_repo.get_scene(db_connection, world.progress.pending_scene_id)
    card = world.progress.pending_negotiation.overture.card.model_copy(
        update={"is_confirmed_by_player": True}
    )
    outcome = TermsCardOutcome(result=TermsResult.AGREED, terms_card=card)

    errors = validate_outcome_against_package(scene.package, outcome)

    assert scene.package.scene_type is SceneType.PEACE
    assert errors == []


async def test_a_declined_ransom_scene_can_be_stored_with_a_refusal_outcome(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = _demand_world()
    await persist_triggered_scene(db_connection, world, SCENARIO)
    scene = await scene_repo.get_scene(db_connection, world.progress.pending_scene_id)
    refusal = TermsCardOutcome(result=TermsResult.REFUSED)

    assert validate_outcome_against_package(scene.package, refusal) == []
