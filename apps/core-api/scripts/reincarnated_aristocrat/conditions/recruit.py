"""Group R: a candidate who agrees to serve joins the House."""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import CHARACTERS, CharacterSpec
from scripts.reincarnated_aristocrat.conditions.common import (
    NO_REPEAT_MARKER,
    NO_VALUE,
    attr,
    change,
    clear,
    label,
)
from scripts.seeding.expr import SET, Cond, Expression, Mut, all_of, eq, ne

RECRUIT_GUARDS: dict[str, Expression] = {
    "lysia": eq("beats.engaged", True),
    "fahm": eq("beats.fahm_findable", True),
    "mireille": eq("beats.mireille_findable", True),
}
JOIN_TEXT = (
    "{name} agrees to serve Ars. Narrate the moment they commit, in their own "
    "voice. Do not state any numbers."
)
REFUSED_TEXT = (
    "That recruitment cannot happen now: the person is already in service or is "
    "not yet available. Narrate that nothing changes."
)


def _join_mutations(spec: CharacterSpec) -> tuple[Mut, ...]:
    mutations = [
        Mut(attr(spec.slug, "is_recruited"), SET, True),
        Mut(attr(spec.slug, "loyalty"), SET, balance.RECRUIT_START_LOYALTY),
        change("time.recruits", 1),
        change("standing", balance.RECRUIT_STANDING),
    ]
    if balance.ARMY_VALUE[spec.slug] > 0:
        mutations.append(change("army_strength", balance.ARMY_VALUE[spec.slug]))
    return (*mutations, *clear("recruit_target"))


def _recruit(index: int, spec: CharacterSpec) -> Cond:
    parts = [
        eq("intent.recruit_target", spec.slug),
        eq(attr(spec.slug, "is_recruited"), False),
    ]
    if spec.slug in RECRUIT_GUARDS:
        parts.append(RECRUIT_GUARDS[spec.slug])
    return Cond(
        label("R", index, f"Recruit {spec.slug}"),
        all_of(*parts),
        _join_mutations(spec),
        instruction=JOIN_TEXT.format(name=spec.name) + NO_REPEAT_MARKER,
    )


def recruit_conditions() -> list[Cond]:
    recruitable = [spec for spec in CHARACTERS if spec.is_recruitable]
    conditions = [_recruit(index, spec) for index, spec in enumerate(recruitable, 1)]
    conditions.append(
        Cond(
            label("R", len(conditions) + 1, "Recruit refused"),
            ne("intent.recruit_target", NO_VALUE),
            clear("recruit_target"),
            instruction=REFUSED_TEXT + NO_REPEAT_MARKER,
        )
    )
    return conditions
