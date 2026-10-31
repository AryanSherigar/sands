from app.engine.pressure.bands import ORDERED_BANDS
from app.engine.rng import DeterministicRng
from app.models.world_diplomacy import AgentState
from strategy_contracts.agents import AgentTrait, AgentTuning
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scenario import StrategyScenario

MAX_LOYALTY = 100
FULL_PERCENT = 100
WEAKNESS_TOPICS = frozenset((RumorTopic.STRAIN, RumorTopic.HEALTH))
AGENT_TRAIT_COUNT = 2
CONTRADICTORY_TRAITS = frozenset((AgentTrait.HONEST, AgentTrait.DECEITFUL))
AGENT_NAMES = (
    "Aldous",
    "Bertrand",
    "Corvin",
    "Desmond",
    "Edric",
    "Fenwick",
    "Godwin",
    "Hadrian",
    "Isolde",
    "Jorund",
    "Kestrel",
    "Leofric",
    "Maren",
    "Nerys",
    "Osric",
    "Perrin",
)


def apply_pious_bonus(
    loyalty: int, traits: list[AgentTrait], tuning: AgentTuning
) -> int:
    if AgentTrait.PIOUS not in traits:
        return loyalty
    return min(MAX_LOYALTY, loyalty + tuning.pious_loyalty_bonus)


def _pick_traits(stream: DeterministicRng) -> list[AgentTrait]:
    picked: list[AgentTrait] = []
    for trait in stream.shuffled(sorted(AgentTrait)):
        if len(picked) == AGENT_TRAIT_COUNT:
            break
        if {*picked, trait} >= CONTRADICTORY_TRAITS:
            continue
        picked.append(trait)
    return picked


def generate_agent(
    scenario: StrategyScenario, rng: DeterministicRng, envoy_id: str
) -> AgentState:
    tuning = scenario.tuning.agents
    stream = rng.fork("agent", envoy_id)
    name = AGENT_NAMES[stream.roll(len(AGENT_NAMES))]
    traits = _pick_traits(stream)
    base_loyalty = stream.roll_range(tuning.loyalty_min, tuning.loyalty_max)
    loyalty = apply_pious_bonus(base_loyalty, traits, tuning)
    return AgentState(name=name, traits=traits, loyalty=loyalty)


def soothing_shift(band: PressureBand, topic: RumorTopic, steps: int) -> PressureBand:
    # NOTE: soothing means the reader feels safer: danger topics read lower, weakness topics read higher.
    direction = 1 if topic in WEAKNESS_TOPICS else -1
    index = ORDERED_BANDS.index(band) + direction * steps
    return ORDERED_BANDS[max(0, min(len(ORDERED_BANDS) - 1, index))]


def agent_wrong_chance(base_chance: int, agent: AgentState, tuning: AgentTuning) -> int:
    chance = base_chance
    if AgentTrait.HONEST in agent.traits:
        chance -= tuning.honest_wrong_reduction_percent
    if AgentTrait.INCOMPETENT in agent.traits:
        chance += tuning.incompetent_wrong_bonus_percent
    return max(0, min(FULL_PERCENT, chance))


def reported_band(
    band: PressureBand,
    topic: RumorTopic,
    agent: AgentState,
    tuning: AgentTuning,
) -> PressureBand:
    if agent.bribed_by is not None:
        return soothing_shift(band, topic, tuning.bribed_calm_steps)
    if AgentTrait.DECEITFUL in agent.traits:
        return soothing_shift(band, topic, tuning.deceitful_calm_steps)
    return band


def bribe_price(agent: AgentState, tuning: AgentTuning) -> int:
    price = tuning.bribe_base_price + tuning.bribe_price_per_loyalty * agent.loyalty
    if AgentTrait.INCOMPETENT in agent.traits:
        price = price * (FULL_PERCENT - tuning.incompetent_bribe_discount_percent)
        price //= FULL_PERCENT
    return price
