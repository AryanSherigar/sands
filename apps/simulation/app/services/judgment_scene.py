from uuid import UUID

from app.engine.diplomacy.prisoners import find_prisoner
from app.engine.judgments.constants import JUDGMENT_EXCHANGE_CAP, MAX_ADVISORS
from app.engine.negotiation import player_faction_id
from app.engine.opinion import opinion_of
from app.engine.peace.hostages import find_hostage
from app.models.world_character import CommanderStatus, GovernorState
from app.models.world_events import PendingJudgment
from app.models.world_state import WorldState
from app.services.negotiation_scene import _mood, _participant
from app.services.scene_package_validation import require_valid_package
from app.services.trait_notes import trait_notes
from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    AdvisorStance,
    JudgmentOption,
    JudgmentOutcome,
    JudgmentSpec,
    JudgmentSubjectKind,
    JudgmentVerdict,
)
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    Participant,
    ParticipantKind,
    SceneInitiator,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
)

SUBJECT_LABEL = "Accused"
CHARGE_LABEL = "Charge"
REGION_LABEL = "Region"
CHARGE_TEXT = {
    "captive_held": "taken captive in battle",
    "hostage_at_mercy": "a hostage whose guarantor broke faith",
    "uprising_crushed": "an uprising in their region has been crushed",
    "uprising_flipped": "their region was lost to rebels",
    "uprising_stage_changed": "an uprising in their region has taken up arms",
}
GOVERNOR_SUMMARY = "{name}, governor of {region}, stands accused before {ruler}."
CAPTIVE_SUMMARY = "{name} of {faction} stands captive before {ruler}."


def _faction_name(scenario: StrategyScenario, faction_id: str) -> str:
    named = next(
        (item.name for item in scenario.factions if item.id == faction_id), None
    )
    return named or faction_id.replace("_", " ").title()


def _governor_participant(
    governor: GovernorState, scenario: StrategyScenario, stance: AdvisorStance | None
) -> Participant:
    return Participant(
        participant_id=governor.id,
        kind=ParticipantKind.GOVERNOR,
        name=governor.name,
        trait_ids=list(governor.trait_ids),
        trait_notes=trait_notes(governor.trait_ids, scenario),
        mood=_mood(governor.opinion_of_ruler),
        stance=stance,
    )


def _character_participant(
    world: WorldState, scenario: StrategyScenario, character_id: str
) -> Participant:
    leader = world.leaders.get(character_id)
    if leader is not None:
        player_leader = world.factions[player_faction_id(world)].leader_id
        return _participant(world, leader, scenario, opinion_of(leader, player_leader))
    commander = world.commanders.get(character_id)
    traits = list(commander.trait_ids) if commander is not None else []
    name = commander.name if commander else character_id.replace("_", " ").title()
    return Participant(
        participant_id=character_id,
        kind=ParticipantKind.COMMANDER,
        name=name,
        trait_ids=traits,
        trait_notes=trait_notes(traits, scenario),
    )


def _accused_participant(
    world: WorldState, scenario: StrategyScenario, pending: PendingJudgment
) -> Participant:
    if pending.subject_kind is JudgmentSubjectKind.GOVERNOR:
        return _governor_participant(
            world.governors[pending.subject_id], scenario, None
        )
    hostage = find_hostage(world, pending.subject_id)
    if hostage is not None:
        return _character_participant(world, scenario, hostage.leader_id)
    prisoner = find_prisoner(world, pending.subject_id)
    assert prisoner is not None and prisoner.character_id is not None
    return _character_participant(world, scenario, prisoner.character_id)


def _court_governors(world: WorldState, accused_id: str) -> list[GovernorState]:
    player_id = player_faction_id(world)
    court = [
        governor
        for governor in world.governors.values()
        if governor.id != accused_id
        and world.regions.get(governor.region_id) is not None
        and world.regions[governor.region_id].owner_id == player_id
    ]
    return sorted(court, key=lambda item: (-item.opinion_of_ruler, item.id))


def _iron_voice(
    world: WorldState,
    scenario: StrategyScenario,
    accused_id: str,
    governors: list[GovernorState],
) -> Participant | None:
    player_id = player_faction_id(world)
    commanders = sorted(
        item.id
        for item in world.commanders.values()
        if item.faction_id == player_id
        and item.status is CommanderStatus.ACTIVE
        and item.id != accused_id
    )
    if commanders:
        voice = _character_participant(world, scenario, commanders[0])
        return voice.model_copy(
            update={"kind": ParticipantKind.OFFICER, "stance": AdvisorStance.IRON}
        )
    if len(governors) > 1:
        return _governor_participant(governors[-1], scenario, AdvisorStance.IRON)
    return None


def select_advisors(
    world: WorldState, accused_id: str, scenario: StrategyScenario
) -> list[Participant]:
    """A mercy voice and an iron voice from the player's court, fewer if the court is thin."""
    governors = _court_governors(world, accused_id)
    advisors: list[Participant] = []
    if governors:
        advisors.append(
            _governor_participant(governors[0], scenario, AdvisorStance.MERCY)
        )
    iron = _iron_voice(world, scenario, accused_id, governors)
    if iron is not None:
        advisors.append(iron)
    return advisors[:MAX_ADVISORS]


def _situation(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingJudgment,
    accused: Participant,
) -> SceneSituation:
    charge = CHARGE_TEXT.get(pending.trigger_event, "awaiting the sovereign's word")
    facts = [SituationFact(label=SUBJECT_LABEL, value=accused.name)]
    facts.append(SituationFact(label=CHARGE_LABEL, value=charge))
    if pending.subject_kind is JudgmentSubjectKind.GOVERNOR:
        region = world.governors[pending.subject_id].region_id
        facts.append(
            SituationFact(label=REGION_LABEL, value=region.replace("_", " ").title())
        )
        summary = GOVERNOR_SUMMARY.format(
            name=accused.name,
            region=region.replace("_", " ").title(),
            ruler=world.ruler.name,
        )
    else:
        summary = CAPTIVE_SUMMARY.format(
            name=accused.name,
            faction=_faction_name(scenario, pending.accused_faction_id),
            ruler=world.ruler.name,
        )
    return SceneSituation(summary=summary, facts=facts)


def _spec(kind: JudgmentSubjectKind) -> JudgmentSpec:
    return JudgmentSpec(
        subject_kind=kind,
        options=[
            JudgmentOption(verdict=verdict, nuances=list(NUANCES_BY_VERDICT[verdict]))
            for verdict in JudgmentVerdict
        ],
    )


def build_judgment_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    pending: PendingJudgment,
) -> ScenePackage:
    accused = _accused_participant(world, scenario, pending)
    advisors = select_advisors(world, accused.participant_id, scenario)
    package = ScenePackage(
        scene_id=scene_id,
        initiator=SceneInitiator.AI,
        is_declinable=False,
        playthrough_id=world.playthrough_id,
        scene_type=SceneType.JUDGMENT,
        turn=world.clock.turn,
        situation=_situation(world, scenario, pending, accused),
        participants=[accused, *advisors],
        allowed_outcomes=[_spec(pending.subject_kind)],
        exchange_cap=JUDGMENT_EXCHANGE_CAP,
        default_outcome=JudgmentOutcome(verdict=JudgmentVerdict.IMPRISON),
    )
    return require_valid_package(package)
