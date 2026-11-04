"""End conditions. First match wins by ascending priority, so the losses that
cannot be recovered from are checked first and the Fear variant before the
ordinary win. Thresholds live in balance.py.
"""

from dataclasses import dataclass

from app.models.end_condition import EndConditionCreate
from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import RECRUITABLE_SLUGS
from scripts.reincarnated_aristocrat.conditions.common import CLOCK, TURNS, attr
from scripts.seeding.expr import Expression, all_of, either, eq, gte, lt, lte

WIN = "win"
LOSE = "lose"


@dataclass(frozen=True)
class Ending:
    key: str
    tag: str
    title: str
    text: str
    is_secret: bool = False


ENDINGS: tuple[Ending, ...] = (
    Ending(
        "coup",
        LOSE,
        "The Household Turns",
        "A lord is only as strong as the people who stand behind him, and Ars had "
        "let the House grow too weak to hold them. When the betrayal came, nobody "
        "moved to stop it. Lamberk passes to other hands, and a boy who once read "
        "everyone's talent but his own learns what he could not see.",
    ),
    Ending(
        "bankruptcy",
        LOSE,
        "The Empty Treasury",
        "Month after month the House could not pay its way. The soldiers went "
        "unpaid, the creditors came, and in the end there was nothing left to "
        "defend. Lamberk's name survives in a ledger of debts.",
    ),
    Ending(
        "famine",
        LOSE,
        "A Hungry Winter",
        "The granaries ran dry and then the villages did. Lamberk's people left "
        "for kinder valleys, and the manor stood quiet over empty fields.",
    ),
    Ending(
        "revolt",
        LOSE,
        "The Valley Rises",
        "Orders stopped being obeyed, then stopped being heard. When the villages "
        "rose, there was no one left in the manor who could say they were wrong.",
    ),
    Ending(
        "collapse",
        LOSE,
        "Too Few Swords",
        "When Couran's call came, Lamberk had too little to offer. The county "
        "chief looked past Ars and chose another, and the House was left to the "
        "mercy of the war it had hoped to use.",
    ),
    Ending(
        "fear",
        WIN,
        "The Lord Everyone Obeys",
        "The county chief names Ars Lord of Canarre, and no one in the hall "
        "mistakes why. His retainers are able, his coffers are full and his "
        "household obeys out of something closer to dread than love. It is "
        "enough to rule, and it is the beginning of a very different story.",
        is_secret=True,
    ),
    Ending(
        "canarre",
        WIN,
        "Lord of Canarre",
        "The county chief names Ars Lord of Canarre. Behind him stand retainers "
        "who chose to serve, a treasury that holds, and a valley that trusts him. "
        "A salaryman who once could only read people's talent has learned to put "
        "it to use, and the war for Missian is only the first thing it will win.",
    ),
    Ending(
        "endures",
        LOSE,
        "Lamberk Endures",
        "The years pass without a great victory or a great ruin. Ars keeps the "
        "valley fed, the household together and the name Louvent respected, and "
        "the world's larger story moves on without him. It is not the rise he "
        "imagined, but Lamberk endures.",
    ),
)


def _readiness() -> list[Expression]:
    return [
        eq("beats.couran_called", True),
        gte("standing", balance.WIN_STANDING),
        gte("control", balance.WIN_CONTROL),
        gte("resources", balance.WIN_RESOURCES),
        gte("funds", balance.WIN_FUNDS),
        gte("army_strength", balance.WIN_ARMY),
        gte("time.recruits", balance.WIN_RECRUITS),
        gte("sheet.competence", balance.WIN_COMPETENCE),
        *(eq(attr(slug, "betrayal_risk"), False) for slug in RECRUITABLE_SLUGS),
        eq(attr("ritsu", "is_recruited"), True),
        eq(attr("charlotte", "is_recruited"), True),
    ]


def _strategist() -> Expression:
    return either(
        eq(attr("rosell", "is_recruited"), True),
        eq(attr("mireille", "is_recruited"), True),
    )


def _expressions() -> dict[str, Expression]:
    fear = [
        gte("sheet.fear", balance.FEAR_WIN_FEAR),
        lte("sheet.goodwill", balance.FEAR_WIN_GOODWILL),
    ]
    return {
        "coup": eq("beats.coup", True),
        "bankruptcy": gte("time.debt_months", balance.RUIN_MONTHS),
        "famine": gte("time.low_resources", balance.RUIN_MONTHS),
        "revolt": gte("time.low_control", balance.RUIN_MONTHS),
        "collapse": all_of(
            eq("beats.couran_called", True),
            lt("army_strength", balance.COLLAPSE_ARMY),
            gte(CLOCK, balance.COURAN_DAY + balance.COLLAPSE_GRACE_DAYS),
        ),
        "fear": all_of(*_readiness(), *fear, _strategist()),
        "canarre": all_of(*_readiness(), _strategist()),
        "endures": gte(TURNS, balance.TIMEOUT_TURNS),
    }


def end_conditions() -> list[EndConditionCreate]:
    expressions = _expressions()
    return [
        EndConditionCreate(
            condition_expression=expressions[ending.key],
            outcome_tag=ending.tag,
            outcome_title=ending.title,
            outcome_text=ending.text,
            is_secret=ending.is_secret,
            priority=priority,
        )
        for priority, ending in enumerate(ENDINGS)
    ]
