from app.engine.events.effects import EffectContext, apply_effect
from app.engine.negotiation import close_negotiation
from app.engine.overtures.arming import arm_overture
from app.engine.overtures.succession_hook import remove_ruler
from app.engine.subjects import Subject
from app.models.world_diplomacy import TruceState
from app.models.world_state import WorldState
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.events import EffectKind, EffectSpec
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import TermsResult

from tests.engine.overtures.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_axes,
)

TUNING = SCENARIO.tuning.peace


def _signed_world() -> tuple[WorldState, TruceState]:
    world = make_world()
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    truce = TruceState(
        id="truce_1",
        faction_a=first,
        faction_b=second,
        expires_turn=world.clock.turn + TUNING.tier_turns[PeaceTier.GENERATION],
        signed_turn=world.clock.turn,
        tier=PeaceTier.GENERATION,
        signatory_leader_ids=[
            world.factions[first].leader_id,
            world.factions[second].leader_id,
        ],
    )
    world.truces.append(truce)
    return world, truce


def _after_death(**axes: int):
    world, truce = _signed_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, **axes) if axes else SCENARIO
    remove_ruler(world, scenario, WRATHFUL_RIVAL)
    return world, scenario, truce


def test_ruler_dies_effect_replaces_leader_with_heir() -> None:
    world, _ = _signed_world()
    old_id = world.factions[WRATHFUL_RIVAL].leader_id
    context = EffectContext(
        world, WRATHFUL_RIVAL, Subject(ConditionScope.FACTION, WRATHFUL_RIVAL), SCENARIO
    )

    changes = apply_effect(context, EffectSpec(kind=EffectKind.RULER_DIES))

    heir_id = world.factions[WRATHFUL_RIVAL].leader_id
    assert heir_id != old_id
    assert world.leaders[old_id].is_alive is False
    assert world.leaders[heir_id].is_alive is True
    assert world.leaders[heir_id].faction_id == WRATHFUL_RIVAL
    assert [change.path for change in changes] == [
        f"factions.{WRATHFUL_RIVAL}.leader_id"
    ]


def test_ruler_dies_on_the_player_faction_is_ignored() -> None:
    world, _ = _signed_world()
    before = world.factions[PLAYER].leader_id

    assert remove_ruler(world, SCENARIO, PLAYER) == []
    assert world.factions[PLAYER].leader_id == before


def test_ruler_death_lapses_signed_treaties_and_queues_renewal() -> None:
    world, _, truce = _after_death()

    assert truce.tier is TUNING.renewal_short_tier
    assert world.overture_renewals == [truce.id]


def test_heir_renewal_overture_arms_next_rollover() -> None:
    world, scenario, truce = _after_death()

    arm_overture(world, scenario)

    pending = world.progress.pending_negotiation
    assert pending is not None
    assert pending.overture.kind is OvertureKind.HEIR_RENEWAL
    assert pending.overture.truce_id == truce.id
    assert pending.initiator_faction_id == WRATHFUL_RIVAL
    assert world.overture_renewals == []


def test_no_renewal_when_counterpart_is_destroyed() -> None:
    world, scenario, _ = _after_death()
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    arm_overture(world, scenario)

    assert world.progress.pending_negotiation is None
    assert world.overture_renewals == []


def test_accepted_renewal_restores_the_original_tier() -> None:
    world, scenario, truce = _after_death()
    arm_overture(world, scenario)
    card = world.progress.pending_negotiation.overture.card
    confirmed = card.model_copy(update={"is_confirmed_by_player": True})

    closed, _ = close_negotiation(
        world, scenario, world.progress.pending_scene_id, confirmed, TermsResult.AGREED
    )

    restored = next(item for item in closed.truces if item.id == truce.id)
    assert restored.tier is PeaceTier.GENERATION
    assert closed.peace.lapses == []


def test_ignored_renewal_repudiates_for_a_resentful_heir() -> None:
    world, scenario, _ = _after_death(pride=3)
    arm_overture(world, scenario)

    closed, _ = close_negotiation(
        world, scenario, world.progress.pending_scene_id, None, TermsResult.REFUSED
    )

    assert closed.peace.lapses == []
    assert len(closed.oathbreakers) == 1


def test_ignored_renewal_for_a_calm_heir_keeps_the_short_truce() -> None:
    world, scenario, truce = _after_death(caution=3)
    arm_overture(world, scenario)

    closed, _ = close_negotiation(
        world, scenario, world.progress.pending_scene_id, None, TermsResult.REFUSED
    )

    kept = next(item for item in closed.truces if item.id == truce.id)
    assert kept.tier is TUNING.renewal_short_tier
    assert closed.oathbreakers == []
