from typing import Final

from strategy_contracts.proclamation import ProclamationBurden, ProclamationDomain

PER_MILLE: Final[int] = 1000

BURDEN_PER_MILLE: Final[dict[ProclamationBurden, int]] = {
    ProclamationBurden.LIGHT: 500,
    ProclamationBurden.MODERATE: 1000,
    ProclamationBurden.SEVERE: 1750,
    ProclamationBurden.RADICAL: 2500,
}

MODIFIER_MANPOWER_REGEN: Final[str] = "manpower_regen_percent"
MODIFIER_UNREST_PER_TURN: Final[str] = "unrest_per_turn"
MODIFIER_TAX_POINTS: Final[str] = "tax_percent_points"
MODIFIER_TRADE_EFFICIENCY: Final[str] = "trade_efficiency_percent"

BASE_IMMEDIATE_EFFECTS: Final[dict[ProclamationDomain, dict[str, int]]] = {
    ProclamationDomain.MARTIAL_LEVIES: {"manpower": 200, "gold": -50, "unrest": 5},
    ProclamationDomain.EMERGENCY_TAXATION: {"gold": 250, "unrest": 15},
    ProclamationDomain.RELIGIOUS_ORTHODOXY: {"gold": -40, "morale": 15},
    ProclamationDomain.NOBLE_PRIVILEGES: {"morale": 10},
    ProclamationDomain.POPULAR_RELIEF: {"unrest": -20, "gold": -100},
}

BASE_ONGOING_MODIFIERS: Final[dict[ProclamationDomain, dict[str, int]]] = {
    ProclamationDomain.MARTIAL_LEVIES: {
        MODIFIER_MANPOWER_REGEN: 25,
        MODIFIER_UNREST_PER_TURN: 3,
    },
    ProclamationDomain.EMERGENCY_TAXATION: {
        MODIFIER_TAX_POINTS: 15,
        MODIFIER_TRADE_EFFICIENCY: -10,
    },
    ProclamationDomain.RELIGIOUS_ORTHODOXY: {
        MODIFIER_UNREST_PER_TURN: -2,
        MODIFIER_TRADE_EFFICIENCY: -5,
    },
    ProclamationDomain.NOBLE_PRIVILEGES: {MODIFIER_TAX_POINTS: -10},
    ProclamationDomain.POPULAR_RELIEF: {MODIFIER_UNREST_PER_TURN: -5},
}

RESCIND_UNREST_PENALTY: Final[int] = 10
PROCLAMATION_MANDATE_COST: Final[int] = 2
DEFAULT_PROCLAMATION_DURATION_TURNS: Final[int] = 4
