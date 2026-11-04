"""Group P: adopting a policy costs Funds or Resources and applies its effects."""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.conditions.common import (
    NO_REPEAT_MARKER,
    NO_VALUE,
    change,
    clear,
    label,
)
from scripts.reincarnated_aristocrat.schema import POLICIES
from scripts.seeding.expr import SET, Cond, Mut, all_of, eq, gte, ne

POLICY_TEXT = {
    "tax_relief": "Ars lowers the levy on the valley's farmers. Show the relief, and the thinner treasury.",
    "farmland_development": "Ars funds new fields and drainage. Show the work beginning; the harvest will come later.",
    "militia_levy": "Ars raises a village militia. Show the muster and the grumbling of men taken from the fields.",
    "fortification": "Ars orders the manor and the valley road fortified. Show the labour and the sense of security.",
    "talent_search": "Ars sends word that Lamberk is looking for skilled people. Show the first replies trickling in.",
    "strict_law": "Ars enforces the law without exception. Show the order it brings and the unease beneath it.",
}
REFUSED_TEXT = (
    "That policy cannot be adopted now: it is already in force or the House "
    "cannot afford it. Narrate that nothing changes."
)


def _cost_mutations(funds: int, resources: int) -> list[Mut]:
    costs = [("funds", funds), ("resources", resources)]
    return [change(path, -amount) for path, amount in costs if amount > 0]


def _policy(index: int, key: str) -> Cond:
    spec = balance.POLICY_SPECS[key]
    mutations = [
        Mut(f"policies.{key}", SET, True),
        *_cost_mutations(spec.funds, spec.resources),
        *(change(path, delta) for path, delta in spec.once),
        *clear("adopt_policy"),
    ]
    return Cond(
        label("P", index, f"Adopt {key}"),
        all_of(
            eq("intent.adopt_policy", key),
            eq(f"policies.{key}", False),
            gte("funds", spec.funds),
            gte("resources", spec.resources),
        ),
        tuple(mutations),
        instruction=POLICY_TEXT[key] + NO_REPEAT_MARKER,
    )


def policy_conditions() -> list[Cond]:
    conditions = [_policy(index, key) for index, key in enumerate(POLICIES, start=1)]
    conditions.append(
        Cond(
            label("P", len(conditions) + 1, "Policy refused"),
            ne("intent.adopt_policy", NO_VALUE),
            clear("adopt_policy"),
            instruction=REFUSED_TEXT + NO_REPEAT_MARKER,
        )
    )
    return conditions
