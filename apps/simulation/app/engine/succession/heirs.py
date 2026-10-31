from app.models.world_character import LeaderState
from strategy_contracts.ids import FactionId, LeaderId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HeirSetup, heir_chain

MAX_ENTITY_ID_CHARS = 40
REGENT_PREFIX = "regent_"
REGENT_NAME = "Regent"


def regent_id_for(faction_id: FactionId) -> LeaderId:
    return f"{REGENT_PREFIX}{faction_id}"[:MAX_ENTITY_ID_CHARS]


def _all_heirs(scenario: StrategyScenario) -> list[HeirSetup]:
    return [heir for setup in scenario.leaders for heir in heir_chain(setup.heir)]


def find_heir_by_id(scenario: StrategyScenario, heir_id: LeaderId) -> HeirSetup | None:
    return next((heir for heir in _all_heirs(scenario) if heir.id == heir_id), None)


def find_heir_setup(
    scenario: StrategyScenario, leader_id: LeaderId
) -> HeirSetup | None:
    for setup in scenario.leaders:
        if setup.id == leader_id:
            return setup.heir
    nested = find_heir_by_id(scenario, leader_id)
    return nested.heir if nested is not None else None


def leader_from_heir(heir: HeirSetup, faction_id: FactionId) -> LeaderState:
    return LeaderState(
        id=heir.id,
        name=heir.name,
        faction_id=faction_id,
        trait_ids=list(heir.trait_ids),
        ambition_ids=list(heir.ambition_ids),
        age=heir.age,
    )


def regent_leader(faction_id: FactionId, scenario: StrategyScenario) -> LeaderState:
    tuning = scenario.tuning.succession
    return LeaderState(
        id=regent_id_for(faction_id),
        name=REGENT_NAME,
        faction_id=faction_id,
        trait_ids=list(tuning.regent_trait_ids),
        ambition_ids=[],
        age=tuning.regent_age,
    )
