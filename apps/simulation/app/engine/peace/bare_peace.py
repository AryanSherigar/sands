from app.models.world_diplomacy import WarState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import PeaceTerm, TermsCard


def build_bare_peace_card(
    war: WarState,
    proposer_id: FactionId,
    counterpart_id: FactionId,
    guarantor_ids: list[FactionId],
    *,
    is_white_peace: bool,
) -> TermsCard:
    peace = PeaceTerm(
        faction_a=war.attacker_id,
        faction_b=war.defender_id,
        tier=PeaceTier.SHORT,
        guarantor_ids=guarantor_ids,
        is_white_peace=is_white_peace,
    )
    return TermsCard(
        proposer_id=proposer_id,
        counterpart_id=counterpart_id,
        terms=[peace],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def mirror_card(card: TermsCard) -> TermsCard:
    return card.model_copy(
        update={"proposer_id": card.counterpart_id, "counterpart_id": card.proposer_id}
    )
