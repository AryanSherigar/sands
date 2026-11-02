from app.engine.trait_axes import axis_totals
from app.models.world_character import LeaderState
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

PROUD = "proud"
GENTLE = "gentle"
PLAIN = "plain"

PRETEXTS: dict[OvertureKind, dict[str, str]] = {
    OvertureKind.PEACE_OFFER: {
        PROUD: "Let it be known that we offer an end to this war, out of mercy.",
        GENTLE: "Too much blood has been spilled. We would gladly make peace.",
        PLAIN: "We propose an end to the fighting on fair terms.",
    },
    OvertureKind.DEMAND: {
        PROUD: "You have lost this war. Pay what is owed, or answer for it.",
        GENTLE: "We regret that it comes to this, but we must ask restitution.",
        PLAIN: "The fortunes of war are plain. We require payment.",
    },
    OvertureKind.CALL_FOR_TALKS: {
        PROUD: "We will hear what you have to say, once.",
        GENTLE: "Perhaps we can still speak before more is lost.",
        PLAIN: "We ask that our envoys meet and talk.",
    },
    OvertureKind.RANSOM_DEMAND: {
        PROUD: "Your people are ours to keep. Pay for them, or leave them to their fate.",
        GENTLE: "Your people are well kept, but we would see them home for a price.",
        PLAIN: "We hold your captives. Name their ransom and they go free.",
    },
    OvertureKind.RANSOM_COUNTER: {
        PROUD: "Your price is an insult. This is what we will pay, and no more.",
        GENTLE: "We cannot meet your price, but we offer what we can for our people.",
        PLAIN: "We counter your ransom with this sum for the captives.",
    },
    OvertureKind.OATH_OFFER: {
        PROUD: "We hold you worthy of our word. Let it be sworn that we will not make war on you.",
        GENTLE: "We value the friendship between our realms and would swear to keep the peace.",
        PLAIN: "We offer a sworn promise that we will not attack you.",
    },
    OvertureKind.HEIR_RENEWAL: {
        PROUD: "The crown has passed to a new hand. Honor the old treaty to us.",
        GENTLE: "A new ruler asks that the peace our elders made be kept.",
        PLAIN: "We seek to renew the treaty signed by the late ruler.",
    },
}


def _temper(leader: LeaderState, scenario: StrategyScenario) -> str:
    totals = axis_totals(leader, scenario)
    proud = totals[TraitAxis.PRIDE] + totals[TraitAxis.AGGRESSION]
    gentle = totals[TraitAxis.CAUTION] + totals[TraitAxis.TRUST]
    if proud > gentle:
        return PROUD
    if gentle > proud:
        return GENTLE
    return PLAIN


def pretext_for(
    kind: OvertureKind, leader: LeaderState, scenario: StrategyScenario
) -> str:
    return PRETEXTS[kind][_temper(leader, scenario)]
