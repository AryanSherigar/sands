from typing import Final

from strategy_contracts.proclamation import ProclamationBurden, ProclamationDomain

BURDEN_FACTORS: Final[dict[ProclamationBurden, float]] = {
    ProclamationBurden.LIGHT: 0.5,
    ProclamationBurden.MODERATE: 1.0,
    ProclamationBurden.SEVERE: 1.75,
    ProclamationBurden.RADICAL: 2.5,
}

BASE_IMMEDIATE_EFFECTS: Final[dict[ProclamationDomain, dict[str, int]]] = {
    ProclamationDomain.MARTIAL_LEVIES: {
        "manpower": 200,
        "gold": -50,
        "unrest": 5,
    },
    ProclamationDomain.EMERGENCY_TAXATION: {
        "gold": 250,
        "unrest": 15,
    },
    ProclamationDomain.RELIGIOUS_ORTHODOXY: {
        "gold": -40,
        "morale": 15,
        "unrest": 0,
    },
    ProclamationDomain.NOBLE_PRIVILEGES: {
        "morale": 10,
        "loyalty": 20,
    },
    ProclamationDomain.POPULAR_RELIEF: {
        "unrest": -20,
        "gold": -100,
    },
}

BASE_ONGOING_MODIFIERS: Final[dict[ProclamationDomain, dict[str, float]]] = {
    ProclamationDomain.MARTIAL_LEVIES: {
        "manpower_regen_delta": 25.0,
        "unrest_delta": 3.0,
    },
    ProclamationDomain.EMERGENCY_TAXATION: {
        "tax_rate_delta": 0.15,
        "wealth_growth_delta": -0.10,
    },
    ProclamationDomain.RELIGIOUS_ORTHODOXY: {
        "unrest_delta": -2.0,
        "trade_efficiency_delta": -0.05,
    },
    ProclamationDomain.NOBLE_PRIVILEGES: {
        "tax_rate_delta": -0.10,
        "command_cost_discount": 0.20,
    },
    ProclamationDomain.POPULAR_RELIEF: {
        "unrest_delta": -5.0,
        "gold_maintenance_delta": 10.0,
    },
}

RESCIND_UNREST_PENALTY: Final[int] = 10
PROCLAMATION_MANDATE_COST: Final[int] = 2
DEFAULT_PROCLAMATION_DURATION_TURNS: Final[int] = 4
