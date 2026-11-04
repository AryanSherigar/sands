"""Group T: training raises one stat of one retainer.

The narrator sets `intent.train_who` and `intent.train_stat`; a condition checks
the retainer, the monthly limit, the cost and the hidden cap, then applies the
gain, the cost and the flags together. The cap is a literal in each expression,
so a gain is never rejected after the House has already paid for it.
"""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import (
    CHARACTERS,
    CharacterSpec,
    attributes_schema,
)
from scripts.reincarnated_aristocrat.conditions.common import (
    NO_REPEAT_MARKER,
    NO_VALUE,
    attr,
    change,
    clear,
    label,
)
from scripts.reincarnated_aristocrat.stats import STAT_LABELS, TRAINABLE_STATS
from scripts.seeding.expr import (
    SET,
    Cond,
    Expression,
    Mut,
    all_of,
    either,
    eq,
    gte,
    lt,
    lte,
    ne,
)

GAIN_TEXT = (
    "{name} trains {stat} this month and improves noticeably. Narrate the "
    "progress in a short scene. Do not state any numbers."
)
LIMIT_TEXT = (
    "{name} has learned all that training can teach in {stat} for now. Narrate "
    "that nothing more can be gained here. Nothing is spent."
)
FAILED_TEXT = (
    "The training cannot happen now: the person is not in Ars's service, has "
    "already trained this month, or the House cannot afford it. Narrate that "
    "nothing changes."
)
Cost = tuple[int, int]


def stat_cap(spec: CharacterSpec, stat: str) -> int:
    return int(attributes_schema(spec)[stat].max or 0)


def _base(spec: CharacterSpec, stat: str) -> list[Expression]:
    return [
        eq("intent.train_who", spec.slug),
        eq("intent.train_stat", stat),
        eq(attr(spec.slug, "is_recruited"), True),
        eq(attr(spec.slug, "has_trained"), False),
    ]


def _outcome(spec: CharacterSpec, stat: str, gain: int, cost: Cost) -> tuple[Mut, ...]:
    path = attr(spec.slug, stat)
    mutations = [
        change(path, gain),
        change("funds", -cost[0]),
        change("resources", -cost[1]),
        Mut(attr(spec.slug, "has_trained"), SET, True),
    ]
    if stat in balance.ARMY_TRAINED_STATS and balance.ARMY_VALUE[spec.slug] > 0:
        mutations.append(change("army_strength", balance.ARMY_PER_TRAINING))
    return (*mutations, *clear("train_who", "train_stat"))


def _gain(index: int, spec: CharacterSpec, stat: str, gain: int, cost: Cost) -> Cond:
    path = attr(spec.slug, stat)
    parts = [*_base(spec, stat)]
    if gain == balance.TRAIN_BIG_GAIN:
        parts.append(lt(path, balance.TRAIN_LOW_BAND_LIMIT))
    parts += [lte(path, stat_cap(spec, stat) - gain), gte("funds", cost[0])]
    parts.append(gte("resources", cost[1]))
    return Cond(
        label("T", index, f"Train {spec.slug} {stat} +{gain}"),
        all_of(*parts),
        _outcome(spec, stat, gain, cost),
        instruction=GAIN_TEXT.format(name=spec.name, stat=STAT_LABELS[stat])
        + NO_REPEAT_MARKER,
    )


def _limit(index: int, spec: CharacterSpec, stat: str) -> Cond:
    return Cond(
        label("T", index, f"Train {spec.slug} {stat} limit"),
        all_of(*_base(spec, stat), gte(attr(spec.slug, stat), stat_cap(spec, stat))),
        clear("train_who", "train_stat"),
        instruction=LIMIT_TEXT.format(name=spec.name, stat=STAT_LABELS[stat])
        + NO_REPEAT_MARKER,
    )


def _target(first_index: int, spec: CharacterSpec, stat: str) -> list[Cond]:
    return [
        _gain(first_index, spec, stat, balance.TRAIN_BIG_GAIN, balance.TRAIN_BIG_COST),
        _gain(
            first_index + 1,
            spec,
            stat,
            balance.TRAIN_SMALL_GAIN,
            balance.TRAIN_SMALL_COST,
        ),
        _limit(first_index + 2, spec, stat),
    ]


def training_conditions() -> list[Cond]:
    conditions: list[Cond] = []
    for spec in (item for item in CHARACTERS if item.is_recruitable):
        for stat in TRAINABLE_STATS:
            conditions += _target(len(conditions) + 1, spec, stat)
    conditions.append(
        Cond(
            label("T", len(conditions) + 1, "Training failed"),
            either(ne("intent.train_who", NO_VALUE), ne("intent.train_stat", NO_VALUE)),
            clear("train_who", "train_stat"),
            instruction=FAILED_TEXT + NO_REPEAT_MARKER,
        )
    )
    return conditions
