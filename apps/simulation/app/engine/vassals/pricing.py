from strategy_contracts.terms import VassalTerm
from strategy_contracts.vassal import VassalTuning


def vassal_price(term: VassalTerm, tuning: VassalTuning) -> int:
    price = (
        term.duration_turns * tuning.price_per_vassal_turn
        if term.duration_turns
        else tuning.price_forever
    )
    price += term.tribute_share_percent * tuning.price_per_tribute_percent
    price += term.levy_share_percent * tuning.price_per_levy_percent
    if term.is_foreign_policy_controlled:
        price += tuning.price_foreign_policy
    if term.has_garrison_rights:
        price += tuning.price_garrison
    return price
