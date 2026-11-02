from uuid import UUID

from app.engine.treaty.conditional_scan import scan_conditional_clauses
from app.engine.treaty.signing import apply_card
from app.models.world_events import PhaseName
from app.services.conditional_projection import project_conditional_clauses
from strategy_contracts.condition_templates import ConditionClause, ConditionTemplate
from strategy_contracts.terms import (
    ConditionalMode,
    ConditionalTerm,
    TermsCard,
    TradeDealTerm,
)
from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

SCENE_ID = UUID(int=77)
LOW_TREASURY = 10_000
LAPSE_TURNS = 8


def _conditional(mode: ConditionalMode, template: ConditionTemplate) -> ConditionalTerm:
    return ConditionalTerm(
        mode=mode,
        when=ConditionClause(template=template, faction_id=PLAYER, value=LOW_TREASURY),
        expires_in_turns=LAPSE_TURNS,
        inner=TradeDealTerm(
            faction_a=PLAYER, faction_b=CAUTIOUS_RIVAL, duration_turns=6
        ),
    )


def _sign(world, term: ConditionalTerm) -> None:
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=CAUTIOUS_RIVAL,
        terms=[term],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )
    apply_card(world, SCENARIO, card, SCENE_ID)


def test_a_trigger_shows_as_pending_to_both_parties_only() -> None:
    world = make_world()
    _sign(
        world, _conditional(ConditionalMode.TRIGGER, ConditionTemplate.TREASURY_ABOVE)
    )

    [mine] = project_conditional_clauses(world, PLAYER)
    [theirs] = project_conditional_clauses(world, CAUTIOUS_RIVAL)

    assert (mine.mode, mine.state, mine.inner_kind) == (
        "trigger",
        "pending",
        "trade_deal",
    )
    assert mine.party_ids == sorted([PLAYER, CAUTIOUS_RIVAL])
    assert theirs.commitment_id == mine.commitment_id
    assert project_conditional_clauses(world, WRATHFUL_RIVAL) == []


def test_a_gate_shows_open_or_closed_with_its_condition() -> None:
    world = make_world()
    world.factions[PLAYER].treasury = LOW_TREASURY + 1
    _sign(world, _conditional(ConditionalMode.GATE, ConditionTemplate.TREASURY_ABOVE))
    [open_gate] = project_conditional_clauses(world, PLAYER)
    assert open_gate.state == "gate_open"

    world.factions[PLAYER].treasury = 0
    scan_conditional_clauses(world, SCENARIO, PhaseName.DIPLOMACY)
    [closed_gate] = project_conditional_clauses(world, PLAYER)
    assert closed_gate.state == "gate_closed"
    assert (closed_gate.template, closed_gate.condition_value) == (
        ConditionTemplate.TREASURY_ABOVE,
        LOW_TREASURY,
    )
