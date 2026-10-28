from enum import Enum


class RejectReason(str, Enum):
    UNKNOWN_FACTION = "unknown_faction"
    FACTION_DESTROYED = "faction_destroyed"
    UNKNOWN_ARMY = "unknown_army"
    NOT_YOUR_ARMY = "not_your_army"
    IN_BATTLE = "in_battle"
    UNKNOWN_REGION = "unknown_region"
    NOT_YOUR_REGION = "not_your_region"
    REGION_OCCUPIED = "region_occupied"
    EMPTY_LEVY = "empty_levy"
    INSUFFICIENT_MANPOWER = "insufficient_manpower"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    LOANS_DISABLED = "loans_disabled"
    INVALID_AMOUNT = "invalid_amount"
    NO_CREDIT = "no_credit"


SHORTFALL_TAKE_LOAN = "shortfall_take_loan"
SHORTFALL_DEFAULT = "shortfall_default"
SHORTFALL_CHOICES = (SHORTFALL_TAKE_LOAN, SHORTFALL_DEFAULT)
