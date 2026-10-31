from uuid import UUID

from app.engine.letters.constants import (
    LETTER_ACK_WARNING,
    LETTER_COOLER,
    LETTER_NO_EFFECT,
    LETTER_WARMER,
)
from app.engine.opinion import opinion_of
from app.models.world_events import PendingLetter
from app.models.world_state import WorldState
from app.services.negotiation_scene import _participant
from app.services.scene_grudges import build_grudges
from app.services.scene_package_validation import require_valid_package
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    ChoiceOption,
    ChoiceOutcome,
    ChoiceSpec,
    HiddenLimits,
    SceneInitiator,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
)

LETTER_EXCHANGE_CAP = 2
TOPIC_LABEL = "Topic"
TOPIC_SUMMARIES = {
    "courtesy": "{sender} writes to {player} in a spirit of courtesy.",
    "warning": "{sender} writes to {player} with a warning.",
    "border_dispute": "{sender} writes to {player} about a disputed border.",
}
REPLY_OPTIONS = (
    ChoiceOption(id=LETTER_WARMER, label="Reply warmly"),
    ChoiceOption(id=LETTER_COOLER, label="Reply coldly"),
    ChoiceOption(id=LETTER_ACK_WARNING, label="Acknowledge the warning"),
    ChoiceOption(id=LETTER_NO_EFFECT, label="Send no particular reply"),
)


def build_letter_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    pending: PendingLetter,
) -> ScenePackage:
    sender = world.factions[pending.sender_faction_id]
    leader = world.leaders[sender.leader_id]
    player_faction_id = next(
        key for key, item in world.factions.items() if item.is_player
    )
    player_leader_id = world.factions[player_faction_id].leader_id
    summary = TOPIC_SUMMARIES[pending.topic].format(
        sender=leader.name, player=world.ruler.name
    )
    package = ScenePackage(
        scene_id=scene_id,
        initiator=SceneInitiator.AI,
        is_declinable=True,
        playthrough_id=world.playthrough_id,
        scene_type=SceneType.LETTER,
        turn=world.clock.turn,
        situation=SceneSituation(
            summary=summary,
            facts=[SituationFact(label=TOPIC_LABEL, value=pending.topic)],
        ),
        participants=[
            _participant(world, leader, scenario, opinion_of(leader, player_leader_id))
        ],
        hidden_limits=HiddenLimits(
            grudges=build_grudges(world, scenario, leader, player_faction_id)
        ),
        allowed_outcomes=[ChoiceSpec(options=list(REPLY_OPTIONS))],
        exchange_cap=LETTER_EXCHANGE_CAP,
        default_outcome=ChoiceOutcome(option_id=LETTER_NO_EFFECT),
    )
    return require_valid_package(package)
