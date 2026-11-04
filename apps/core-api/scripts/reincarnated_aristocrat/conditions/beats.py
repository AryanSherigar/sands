"""Group B: the canon story beats, fired by the clock.

The per-turn base clock advance already guarantees every threshold is reached,
so no separate turn-count backstop is needed.
"""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.conditions.common import CLOCK, change, label
from scripts.seeding.expr import SET, Cond, Expression, Mut, all_of, eq, gte

SHAKEN_CONTROL = 8
ILLNESS_CONTROL = 3
FINDABLE_DELAY_DAYS = 60

ENGAGEMENT_TEXT = (
    "Word comes from Torbekistan: Lord Hamand Plaid recalls the promise he made "
    "with Raven years ago, that his eldest daughter Lysia would marry Raven's "
    "eldest son. Present the engagement this turn. Lysia can now be met and "
    "recruited if the player seeks her out."
)
ILLNESS_TEXT = (
    "Raven's health begins to fail. Show it quietly this turn: a missed meal, a "
    "cough he waves away, a household that pretends not to notice. From now on he "
    "tires easily and the household leans on Ars."
)
DEATH_TEXT = (
    "Raven Louvent dies this turn, after a long illness. Play the farewell with "
    "restraint: he entrusts Ars with the house, his mother Sofia, and Kreiz and "
    "Wren, and asks him to use his gift for the people of Lamberk. Ars becomes "
    "head of House Louvent. The household watches to see what kind of lord he "
    "will be."
)
COURAN_TEXT = (
    "News arrives: Couran Saremakia, the Missian governor's eldest son, has raised "
    "an army against his brother. Missian is splitting in two. Make clear that "
    "Canare's county chief will weigh what Ars has built when deciding whom to "
    "trust and whom to reward."
)
FAHM_TEXT = (
    "Rumours reach Lamberk of a band of mercenaries called the Shadows, said to "
    "slip into any house unseen. Their leader can be found in a back-street tavern "
    "in town. Mention the rumour once and let the player pursue it."
)
MIREILLE_TEXT = (
    "A drifting former noblewoman has been seen in the taverns of Lamberk, "
    "drinking away her savings, and the Shadows speak of her with respect. Mention "
    "her once and let the player pursue it."
)


def _beat(
    index: int, name: str, when: Expression, effects: tuple[Mut, ...], text: str
) -> Cond:
    return Cond(
        label("B", index, name),
        when,
        (Mut(f"beats.{name}", SET, True), *effects),
        instruction=text,
        is_one_shot=True,
    )


def beat_conditions() -> list[Cond]:
    dead = eq("beats.raven_dead", True)
    return [
        _beat(1, "engaged", gte(CLOCK, balance.ENGAGEMENT_DAY), (), ENGAGEMENT_TEXT),
        _beat(
            2,
            "illness_begun",
            gte(CLOCK, balance.ILLNESS_DAY),
            (change("control", -ILLNESS_CONTROL),),
            ILLNESS_TEXT,
        ),
        _beat(
            3,
            "raven_dead",
            all_of(gte(CLOCK, balance.DEATH_DAY), eq("beats.illness_begun", True)),
            (change("control", -SHAKEN_CONTROL),),
            DEATH_TEXT,
        ),
        _beat(
            4,
            "couran_called",
            all_of(gte(CLOCK, balance.COURAN_DAY), dead),
            (),
            COURAN_TEXT,
        ),
        _beat(5, "fahm_findable", dead, (), FAHM_TEXT),
        _beat(
            6,
            "mireille_findable",
            all_of(dead, gte(CLOCK, balance.DEATH_DAY + FINDABLE_DELAY_DAYS)),
            (),
            MIREILLE_TEXT,
        ),
    ]
