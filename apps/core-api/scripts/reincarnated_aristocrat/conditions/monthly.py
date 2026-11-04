"""Group M: once a month the House earns, pays upkeep and drifts.

`time.next_income_day` is a due date the clock catches up with, so each month is
processed once; if the clock jumps several months, one month is processed per
turn until it catches up. The closing condition advances the due date last, so
every other monthly condition in the group sees the same "due" state. The
month counters and the unpaid check run first, on the funds the month started
with: income is always above the unpaid threshold, so checking after it would
never find a month unpaid.
"""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import CHARACTERS
from scripts.reincarnated_aristocrat.conditions.common import (
    NEXT_INCOME,
    attr,
    change,
    is_due,
    is_recruited,
    label,
)
from scripts.seeding.expr import (
    INCREMENT,
    SET,
    Cond,
    Expression,
    Mut,
    all_of,
    eq,
    gt,
    gte,
    lt,
    lte,
)

SHEET_PATHS = {
    "goodwill": "sheet.goodwill",
    "fear": "sheet.fear",
    "competence": "sheet.competence",
}
RECRUITABLE = [spec for spec in CHARACTERS if spec.is_recruitable]
CONTROL_FLOOR_FOR_RESOURCES = 40


class _Counter:
    def __init__(self) -> None:
        self.value = 0

    def next(self) -> int:
        self.value += 1
        return self.value


def _due(*parts: Expression) -> Expression:
    return all_of(is_due(), *parts)


def upkeep(counter: _Counter) -> list[Cond]:
    return [
        Cond(
            label("M", counter.next(), f"Upkeep {spec.slug}"),
            _due(is_recruited(spec.slug)),
            (change("funds", -balance.UPKEEP_PER_RETAINER),),
        )
        for spec in RECRUITABLE
    ]


def policy_effects(counter: _Counter) -> list[Cond]:
    return [
        Cond(
            label("M", counter.next(), f"Policy {key}"),
            _due(eq(f"policies.{key}", True)),
            tuple(change(path, delta) for path, delta in spec.monthly),
        )
        for key, spec in balance.POLICY_SPECS.items()
        if spec.monthly
    ]


def income(counter: _Counter) -> list[Cond]:
    rows: tuple[tuple[str, Expression, str, int], ...] = (
        ("Base income", is_due(), "funds", balance.BASE_INCOME),
        (
            "Control bonus",
            _due(gte("control", balance.HIGH_BAND)),
            "funds",
            balance.INCOME_BONUS,
        ),
        (
            "Resources bonus",
            _due(gte("resources", balance.HIGH_BAND)),
            "funds",
            balance.INCOME_BONUS,
        ),
        (
            "Control penalty",
            _due(lt("control", balance.LOW_BAND)),
            "funds",
            -balance.INCOME_PENALTY,
        ),
        (
            "Resources penalty",
            _due(lt("resources", balance.LOW_BAND)),
            "funds",
            -balance.INCOME_PENALTY,
        ),
        (
            "Harvest",
            _due(gte("control", CONTROL_FLOOR_FOR_RESOURCES)),
            "resources",
            balance.BASE_RESOURCES,
        ),
        (
            "Thin harvest",
            _due(lt("control", CONTROL_FLOOR_FOR_RESOURCES)),
            "resources",
            balance.LOW_RESOURCES_INCOME,
        ),
        ("Fear fades", _due(gt("sheet.fear", 10)), "sheet.fear", -balance.FEAR_DECAY),
    )
    return [
        Cond(label("M", counter.next(), name), when, (change(path, delta),))
        for name, when, path, delta in rows
    ]


def competence(counter: _Counter) -> list[Cond]:
    up, down = balance.COMPETENCE_UP, -balance.COMPETENCE_DOWN
    step = balance.COMPETENCE_GOODWILL_STEP
    rows: tuple[tuple[str, Expression, int], ...] = (
        ("Order is firm", _due(gte("control", balance.HIGH_BAND)), up),
        ("Order is slipping", _due(lt("control", balance.LOW_BAND)), down),
        ("Stores are full", _due(gte("resources", balance.HIGH_BAND)), up),
        ("Stores are thin", _due(lt("resources", balance.LOW_BAND)), down),
        ("Loved lord", _due(gte("sheet.goodwill", balance.HIGH_BAND)), step),
        ("Resented lord", _due(lte("sheet.goodwill", balance.LOW_BAND)), -step),
        (
            "Treasury in debt",
            _due(gt("time.debt_months", 0)),
            -balance.COMPETENCE_DEBT_LOSS,
        ),
        (
            "Treasury is rich",
            _due(
                eq("time.debt_months", 0), gte("funds", balance.COMPETENCE_RICH_FUNDS)
            ),
            step,
        ),
    )
    return [
        Cond(
            label("M", counter.next(), name), when, (change("sheet.competence", delta),)
        )
        for name, when, delta in rows
    ]


def counters(counter: _Counter) -> list[Cond]:
    rows = (
        ("Unpaid", "funds", balance.UNPAID_BELOW, "time.debt_months"),
        ("Hungry", "resources", balance.DISTRESS_BELOW, "time.low_resources"),
        ("Lawless", "control", balance.DISTRESS_BELOW, "time.low_control"),
    )
    conditions: list[Cond] = []
    for name, source, limit, path in rows:
        conditions.append(
            Cond(
                label("M", counter.next(), f"{name} month"),
                _due(lt(source, limit)),
                (Mut(path, INCREMENT, 1),),
            )
        )
        conditions.append(
            Cond(
                label("M", counter.next(), f"{name} recovered"),
                _due(gte(source, limit), gt(path, 0)),
                (Mut(path, SET, 0),),
            )
        )
    return conditions


def unpaid_loyalty(counter: _Counter) -> list[Cond]:
    return [
        Cond(
            label("M", counter.next(), f"Unpaid {spec.slug}"),
            _due(is_recruited(spec.slug), lt("funds", balance.UNPAID_BELOW)),
            (change(attr(spec.slug, "loyalty"), -balance.UNPAID_LOYALTY_LOSS),),
        )
        for spec in RECRUITABLE
    ]


def _reaction_expression(slug: str, rule: balance.Reaction) -> Expression:
    path = SHEET_PATHS[rule.sheet_field]
    test = gte(path, rule.threshold) if rule.is_at_least else lte(path, rule.threshold)
    return _due(is_recruited(slug), test)


def trait_reactions(counter: _Counter) -> list[Cond]:
    return [
        Cond(
            label("M", counter.next(), f"{spec.slug} {rule.stat} {rule.sheet_field}"),
            _reaction_expression(spec.slug, rule),
            (change(attr(spec.slug, rule.stat), rule.delta),),
        )
        for spec in RECRUITABLE
        for rule in balance.TRAIT_REACTIONS[spec.trait]
    ]


def close_month(counter: _Counter) -> list[Cond]:
    resets = tuple(
        Mut(attr(spec.slug, "has_trained"), SET, False) for spec in RECRUITABLE
    )
    return [
        Cond(
            label("M", counter.next(), "Close the month"),
            is_due(),
            (change(NEXT_INCOME, balance.MONTH_DAYS), *resets),
        )
    ]


def monthly_conditions() -> list[Cond]:
    counter = _Counter()
    return [
        *counters(counter),
        *unpaid_loyalty(counter),
        *upkeep(counter),
        *policy_effects(counter),
        *income(counter),
        *competence(counter),
        *trait_reactions(counter),
        *close_month(counter),
    ]
