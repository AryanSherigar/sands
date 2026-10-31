from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.letters.eligibility import eligible_senders, letter_topic
from app.models.world_events import PendingLetter
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def letter_scene_id(world: WorldState, sender_faction_id: FactionId) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{world.playthrough_id}:letter:{world.clock.turn}:{sender_faction_id}",
    )


def arm_letter(world: WorldState, scenario: StrategyScenario) -> None:
    """Pause planning on one letter from the first eligible rival, if letters are on."""
    letters = scenario.tuning.letters
    if not letters.is_enabled or world.progress.pending_scene_id is not None:
        return
    senders = eligible_senders(world)
    if not senders:
        return
    sender = senders[0]
    cooldown_until = world.clock.turn + letters.cooldown_turns
    world.letter_cooldowns[sender] = cooldown_until
    world.progress.pending_scene_id = letter_scene_id(world, sender)
    world.progress.negotiation_counterpart_id = sender
    world.progress.pending_letter = PendingLetter(
        sender_faction_id=sender,
        topic=letter_topic(world, sender).value,
        cooldown_until_turn=cooldown_until,
    )
