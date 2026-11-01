from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.campaign import begin_campaign
from app.engine.commands.application import accept_command
from app.engine.world_init import new_world
from app.models.orders import AnswerEventOrder
from app.models.world_state import WorldState
from app.services.world_projection import project_world
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import make_world

PLAYTHROUGH_ID = UUID("11111111-1111-1111-1111-111111111111")
PLAYER = "house_carrow"
HIGH_UNREST = 70
EASE_COST = 1
DIGEST = "digest"
VERSION = 1


def _scenario():
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = 100
    return scenario


def _fired_world() -> WorldState:
    scenario = _scenario()
    world = new_world(scenario, PLAYTHROUGH_ID, 7, PLAYER, make_world().ruler)
    home = next(r.id for r in world.regions.values() if r.owner_id == PLAYER)
    world.regions[home].unrest = HIGH_UNREST
    return begin_campaign(world, scenario).world


def _grievance(world: WorldState):
    return next(p for p in world.pending_events if p.template_id == "tax_grievance")


def test_pending_event_is_projected_with_choices_costs_and_neglect() -> None:
    world = _fired_world()
    view = project_world(world, _scenario(), VERSION, DIGEST)
    event = next(e for e in view.pending_events if e.template_id == "tax_grievance")
    assert event.subject_kind is ConditionScope.REGION
    assert event.subject_id == _grievance(world).subject_id
    assert event.subject_name
    assert event.region_id == event.subject_id
    assert event.max_tier == 3
    assert event.cause_inputs["region_unrest"] >= HIGH_UNREST - 10
    assert [choice.id for choice in event.choices] == [
        "ease_taxes",
        "garrison_crackdown",
    ]
    ease = event.choices[0]
    assert ease.order_cost == EASE_COST
    assert ease.is_affordable
    assert {preview.kind.value for preview in ease.effects} == {"region_unrest", "gold"}
    assert {p.kind.value for p in event.neglect_effects} == {
        "region_unrest",
        "governor_opinion",
    }
    assert event.queued_choice_id is None


def test_unaffordable_choice_is_flagged() -> None:
    world = _fired_world()
    world.factions[PLAYER].orders_remaining = 0
    view = project_world(world, _scenario(), VERSION, DIGEST)
    event = next(e for e in view.pending_events if e.template_id == "tax_grievance")
    assert not any(choice.is_affordable for choice in event.choices)


def test_queued_answer_is_visible_on_the_event_and_in_the_order_bar() -> None:
    world = _fired_world()
    event_id = _grievance(world).id
    identity = str(uuid5(NAMESPACE_URL, "op"))
    queued = accept_command(
        world,
        _scenario(),
        AnswerEventOrder(faction_id=PLAYER, event_id=event_id, choice_id="ease_taxes"),
        command_id=identity,
        operation_id="op",
        actor_id="actor",
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    ).world
    view = project_world(queued, _scenario(), VERSION, DIGEST)
    event = next(e for e in view.pending_events if e.id == event_id)
    assert event.queued_choice_id == "ease_taxes"
    assert event.queued_command_id == identity
    assert [order.id for order in view.queued_orders] == [identity]
    assert view.queued_orders[0].cost == EASE_COST


def test_fired_event_leaves_a_memory_in_the_view() -> None:
    world = _fired_world()
    view = project_world(world, _scenario(), VERSION, DIGEST)
    memory = next(m for m in view.event_memories if m.template_id == "tax_grievance")
    assert memory.last_tier >= 1
    assert memory.max_tier == 3
    assert memory.subject_name


def test_npc_event_memories_are_not_projected_to_the_player() -> None:
    from app.models.world_event_memory import EventMemory

    world = _fired_world()
    rival = next(
        faction_id
        for faction_id, faction in world.factions.items()
        if not faction.is_player
    )
    world.event_memories.append(
        EventMemory(template_id="bad_harvest", subject_id=rival, last_tier=2, scar=30)
    )

    view = project_world(world, _scenario(), VERSION, DIGEST)

    assert all(memory.subject_id != rival for memory in view.event_memories)
