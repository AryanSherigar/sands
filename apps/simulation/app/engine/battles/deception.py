from app.models.battle_intelligence import PreparationHint
from app.models.world_battle import BattleContingent, BattleState
from strategy_contracts.battle import Tactic


def preparation_hint(contingent: BattleContingent) -> PreparationHint:
    hints = {
        Tactic.HOLD: PreparationHint.HOLDING,
        Tactic.PRESS: PreparationHint.ADVANCING,
        Tactic.FLANK: PreparationHint.FLANKING,
    }
    return hints[contingent.plan.tactic]


def false_hint(hint: PreparationHint) -> PreparationHint:
    hints = tuple(PreparationHint)
    return hints[(hints.index(hint) + 1) % len(hints)]


def has_deception(battle: BattleState, contingent: BattleContingent) -> bool:
    expiry = contingent.deception_expires_exchange
    return expiry is not None and expiry >= battle.total_exchanges + 1


def activate_deception(battle: BattleState, contingent: BattleContingent) -> None:
    contingent.deception_expires_exchange = battle.total_exchanges + 1
