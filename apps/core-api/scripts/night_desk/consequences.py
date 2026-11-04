"""Mutation bundles shared by rule-check options, handlers and backstops."""

from scripts.night_desk import balance
from scripts.night_desk.expr import DECREMENT, INCREMENT, SET, Mut


def _violation(rule: str, penalty: int) -> tuple[Mut, ...]:
    return (
        Mut("sanity", DECREMENT, penalty),
        Mut("violations_count", INCREMENT, 1),
        Mut(f"rule_status.{rule}", SET, "violated"),
    )


def soft_violation(rule: str) -> tuple[Mut, ...]:
    return _violation(rule, balance.SOFT_PENALTY)


def cardinal_violation(rule: str) -> tuple[Mut, ...]:
    return _violation(rule, balance.CARDINAL_PENALTY)


def unsafe_entry() -> tuple[Mut, ...]:
    return _violation("r4", balance.UNSAFE_ENTRY_PENALTY)


def escalation() -> tuple[Mut, ...]:
    return (
        Mut("sanity", DECREMENT, balance.FLINCH),
        Mut("flags.escalations", INCREMENT, 1),
    )
