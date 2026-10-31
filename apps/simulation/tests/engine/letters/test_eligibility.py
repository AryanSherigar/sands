from app.engine.letters.eligibility import eligible_senders, letter_topic
from app.models.world_diplomacy import RelationState, RelationStatus
from strategy_contracts.letters import LetterTopic

from tests.engine.letters.builders import (
    PLAYER,
    RIVAL,
    RIVAL_LEADER,
    TURN,
    letter_world,
    set_opinion,
)


def test_sender_needs_a_leader_memory_or_opinion_reason_toward_the_player() -> None:
    assert eligible_senders(letter_world(is_remembered=False)) == []
    assert eligible_senders(letter_world()) == [RIVAL]
    world = letter_world(is_remembered=False)
    set_opinion(world, 3)
    assert eligible_senders(world) == [RIVAL]


def test_a_destroyed_sender_is_skipped() -> None:
    world = letter_world()
    world.factions[RIVAL].is_destroyed = True
    assert eligible_senders(world) == []


def test_a_leaderless_or_dead_sender_is_skipped() -> None:
    leaderless = letter_world()
    leaderless.factions[RIVAL].leader_id = None
    assert eligible_senders(leaderless) == []
    dead = letter_world()
    dead.leaders[RIVAL_LEADER].is_alive = False
    assert eligible_senders(dead) == []


def test_a_sender_at_war_with_the_player_is_skipped() -> None:
    world = letter_world()
    world.relations.append(
        RelationState(
            faction_a=RIVAL, faction_b=PLAYER, status=RelationStatus.WAR, since_turn=1
        )
    )
    assert eligible_senders(world) == []


def test_the_player_never_writes_to_themselves() -> None:
    world = letter_world()
    assert PLAYER not in eligible_senders(world)


def test_cooldown_blocks_the_sender_until_its_turn() -> None:
    world = letter_world()
    world.letter_cooldowns[RIVAL] = TURN + 1
    assert eligible_senders(world) == []
    world.letter_cooldowns[RIVAL] = TURN
    assert eligible_senders(world) == [RIVAL]


def test_topic_is_warning_for_a_negative_opinion() -> None:
    world = letter_world()
    set_opinion(world, -4)
    assert letter_topic(world, RIVAL) is LetterTopic.WARNING


def test_topic_is_border_dispute_when_the_sender_claims_a_player_region() -> None:
    world = letter_world()
    world.regions["carrow_vale"].claimant_ids = [RIVAL]
    assert letter_topic(world, RIVAL) is LetterTopic.BORDER_DISPUTE


def test_warning_outranks_a_border_dispute() -> None:
    world = letter_world()
    set_opinion(world, -4)
    world.regions["carrow_vale"].claimant_ids = [RIVAL]
    assert letter_topic(world, RIVAL) is LetterTopic.WARNING


def test_topic_is_courtesy_otherwise() -> None:
    assert letter_topic(letter_world(), RIVAL) is LetterTopic.COURTESY
