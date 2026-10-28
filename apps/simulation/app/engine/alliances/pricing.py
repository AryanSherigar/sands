from strategy_contracts.alliance import AllianceTuning, AllianceType
from strategy_contracts.terms import AllianceTerm


def alliance_price(term: AllianceTerm, tuning: AllianceTuning) -> int:
    price = (
        term.duration_turns * tuning.price_per_alliance_turn
        if term.duration_turns
        else tuning.price_forever
    )
    if term.alliance_type is AllianceType.OFFENSIVE:
        price += tuning.price_offensive_extra
    if term.is_separate_peace_banned:
        price += tuning.price_no_separate_peace_extra
    return price
