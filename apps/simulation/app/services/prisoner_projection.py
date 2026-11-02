from app.models.api_world_view import PrisonerView
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

TITLE_COMMANDER = "Commander"
TITLE_RULER = "Ruler"
TITLE_NOBLE = "Noble"


def _identity(world: WorldState, character_id: str) -> tuple[str, str]:
    leader = world.leaders.get(character_id)
    if leader is not None:
        return leader.name, TITLE_RULER
    commander = world.commanders.get(character_id)
    if commander is not None:
        return commander.name, TITLE_COMMANDER
    return character_id.replace("_", " ").title(), TITLE_NOBLE


def _view(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> PrisonerView:
    name, title = _identity(world, prisoner.character_id or prisoner.id)
    return PrisonerView(
        id=prisoner.id,
        name=name,
        title=title,
        origin_faction_id=prisoner.origin_faction_id,
        ransom_value_gold=scenario.tuning.peace.ransom_gold_per_character,
        sentence_ends_turn=prisoner.sentence_ends_turn,
    )


def project_prisoners(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[PrisonerView]:
    held = [
        item
        for item in world.prisoners
        if item.kind is PrisonerKind.CHARACTER and item.held_by_id == faction_id
    ]
    return [_view(world, scenario, item) for item in sorted(held, key=lambda i: i.id)]
