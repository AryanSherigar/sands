from app.engine.coalitions.registry import coalition_against
from app.engine.coalitions.threat import compute_threat
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.negotiation import opinion_of
from app.engine.outrage.status import outrage_value
from app.engine.pressure.agents import agent_wrong_chance, reported_band
from app.engine.pressure.bands import ORDERED_BANDS, to_band
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.engine.rng import DeterministicRng
from app.engine.succession.health import health_band
from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import AgentState, EnvoyState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_pressure import RumorState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HealthBand
from strategy_contracts.traits import TraitAxis

REPORTED_TOPICS = (RumorTopic.WILL, RumorTopic.STRAIN)
RUMOR_MEMORY_TURNS = 5
OPINION_DIVISOR = 5
CUNNING_STEP = 5
FULL_PERCENT = 100
MIDDLE_INDEX = ORDERED_BANDS.index(PressureBand.MEDIUM)


HEALTH_TO_BAND = {
    HealthBand.ROBUST: PressureBand.LOW,
    HealthBand.AILING: PressureBand.HIGH,
    HealthBand.FAILING: PressureBand.VERY_HIGH,
}


def _health_reading(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> PressureBand:
    leader = world.leaders[world.factions[faction_id].leader_id or ""]
    return HEALTH_TO_BAND[health_band(leader, scenario)]


def _coalition_reading(world: WorldState, faction_id: FactionId) -> int:
    coalition = coalition_against(world, faction_id)
    others = len([other for other in world.factions if other != faction_id])
    if coalition is None or not others:
        return 0
    return len(coalition.member_ids) * FULL_PERCENT // others


def _true_band(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    topic: RumorTopic,
) -> PressureBand:
    if topic is RumorTopic.HEALTH:
        return _health_reading(world, scenario, faction_id)
    if topic is RumorTopic.COALITION:
        value = _coalition_reading(world, faction_id)
    elif topic is RumorTopic.THREAT:
        value = compute_threat(world, scenario, faction_id).value
    elif topic is RumorTopic.RAGE:
        value = outrage_value(world, faction_id)
    elif topic is RumorTopic.WILL:
        value = compute_will(world, scenario, faction_id).value
    else:
        value = compute_strain(world, scenario, faction_id).value
    return to_band(value, scenario.tuning.pressure)


def _toward_middle(band: PressureBand) -> PressureBand:
    index = ORDERED_BANDS.index(band)
    step = 1 if index < MIDDLE_INDEX else -1
    return ORDERED_BANDS[index + step]


def _active_agent(scenario: StrategyScenario, envoy: EnvoyState) -> AgentState | None:
    return envoy.agent if scenario.tuning.agents.is_enabled else None


def _wrong_chance(
    world: WorldState, scenario: StrategyScenario, envoy: EnvoyState
) -> int:
    observer = world.leaders[world.factions[envoy.from_faction_id].leader_id or ""]
    target = world.leaders[world.factions[envoy.at_faction_id].leader_id or ""]
    warmth = opinion_of(target, observer.id) // OPINION_DIVISOR
    cunning = axis_totals(observer, scenario)[TraitAxis.CUNNING] * CUNNING_STEP
    base = scenario.tuning.pressure.wrong_hint_base_percent
    chance = max(0, min(FULL_PERCENT, base - warmth - cunning))
    agent = _active_agent(scenario, envoy)
    if agent is None:
        return chance
    return agent_wrong_chance(chance, agent, scenario.tuning.agents)


def _is_corroborated(world: WorldState, envoy: EnvoyState, topic: RumorTopic) -> bool:
    return any(
        rumor.about_faction_id == envoy.at_faction_id
        and rumor.topic is topic
        and rumor.turn == world.clock.turn
        and rumor.envoy_id != envoy.id
        for rumor in world.pressure.rumors
    )


def _hinted_band(
    world: WorldState,
    scenario: StrategyScenario,
    rng: DeterministicRng,
    envoy: EnvoyState,
    topic: RumorTopic,
) -> tuple[PressureBand, bool]:
    true_band = _true_band(world, scenario, envoy.at_faction_id, topic)
    agent = _active_agent(scenario, envoy)
    if agent is None and _is_corroborated(world, envoy, topic):
        return true_band, False
    chance = _wrong_chance(world, scenario, envoy)
    stream = rng.fork("rumor_wrong", envoy.id, world.clock.turn, topic.value)
    band = (
        _toward_middle(true_band) if stream.roll(FULL_PERCENT) < chance else true_band
    )
    if agent is not None:
        band = reported_band(band, topic, agent, scenario.tuning.agents)
    return band, band is not true_band


def _topics_for(world: WorldState, envoy: EnvoyState) -> tuple[RumorTopic, ...]:
    topics = REPORTED_TOPICS if wars_of(world, envoy.at_faction_id) else ()
    if world.coalition_ruleset:
        topics = (*topics, RumorTopic.THREAT)
    if world.coalition_ruleset and coalition_against(world, envoy.at_faction_id):
        topics = (*topics, RumorTopic.COALITION)
    if world.succession_ruleset:
        topics = (*topics, RumorTopic.HEALTH)
    return (*topics, RumorTopic.RAGE) if world.outrage_ruleset else topics


def _can_report(world: WorldState, envoy: EnvoyState) -> bool:
    observer = world.factions[envoy.from_faction_id]
    target = world.factions[envoy.at_faction_id]
    is_live = not observer.is_destroyed and not target.is_destroyed
    return is_live and bool(observer.leader_id and target.leader_id)


def _is_unremarkable(band: PressureBand, topic: RumorTopic) -> bool:
    if topic is RumorTopic.COALITION:
        return False
    if topic in (RumorTopic.THREAT, RumorTopic.RAGE, RumorTopic.HEALTH):
        return ORDERED_BANDS.index(band) <= MIDDLE_INDEX
    return band is PressureBand.MEDIUM


def _file_rumor(
    world: WorldState,
    scenario: StrategyScenario,
    rng: DeterministicRng,
    envoy: EnvoyState,
    topic: RumorTopic,
) -> RumorState | None:
    true_band = _true_band(world, scenario, envoy.at_faction_id, topic)
    if _is_unremarkable(true_band, topic):
        return None
    check = rng.fork("rumor_report", envoy.id, world.clock.turn, topic.value)
    if check.roll(FULL_PERCENT) >= scenario.tuning.pressure.rumor_report_percent:
        return None
    band, is_wrong = _hinted_band(world, scenario, rng, envoy, topic)
    if _active_agent(scenario, envoy) is not None and _is_unremarkable(band, topic):
        return None
    return RumorState(
        id=f"rumor_{next_counter(world, CounterKind.RUMOR)}",
        observer_id=envoy.from_faction_id,
        about_faction_id=envoy.at_faction_id,
        envoy_id=envoy.id,
        topic=topic,
        band=band,
        line_key=f"{topic.value}.{band.value}",
        turn=world.clock.turn,
        is_hint_wrong=is_wrong,
    )


def file_rumors(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    cutoff = world.clock.turn - RUMOR_MEMORY_TURNS
    world.pressure.rumors = [r for r in world.pressure.rumors if r.turn > cutoff]
    events: list[EventLogEntry] = []
    for envoy in sorted(world.envoys, key=lambda item: item.id):
        if not _can_report(world, envoy):
            continue
        for topic in _topics_for(world, envoy):
            rumor = _file_rumor(world, scenario, rng, envoy, topic)
            if rumor is not None:
                world.pressure.rumors.append(rumor)
                events.append(
                    diplomacy_event(
                        "rumor_filed",
                        [rumor.id, rumor.observer_id, rumor.about_faction_id],
                        phase=PhaseName.TIME,
                    )
                )
    return events
