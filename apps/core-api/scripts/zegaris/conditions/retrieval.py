"""Group R: the Ruinkrag bounty, narrated from the code-owned mission stage.

The game owns the stage (quests.retrieval.stage). These conditions only tell the
narrator what the current stage looks like, and keep the soldier's fate open.
"""

from scripts.seeding.expr import Cond, all_of, eq
from scripts.zegaris.conditions.common import RETRIEVAL, at, label

OFFERED_TEXT = (
    "At the Hall of the Deep, a Council captain offers a bounty. A veteran "
    "squad was forced into a chaotic retreat from the fissures; one squadmate "
    "was killed and the body was left in the dark. The Council hires "
    "outsiders to go down with the bloodied squad, recover the body and "
    "burn it, so grieving soldiers need not do it themselves and weaken their "
    "nerves. When the player agrees, propose the accept_retrieval event."
)
ACCEPTED_TEXT = (
    "The player is hired to recover the fallen soldier's body. A Trelium "
    "harpoon may be lent for the descent. A short exposure to Trelium does "
    "not mutate a newcomer."
)
SHAFT_TEXT = (
    "In the deep chamber the soldier is not lying in blood. Out of the dark "
    "walks the soldier, unblemished and smiling with unnatural peaceful warmth, "
    "whispering: 'I'm not dead. Put down your weapons. There is hope down "
    "here... you don't have to fight anymore.' NEVER confirm whether this is "
    "the living soldier, an abomination wearing the voice, or false hope "
    "taking root. Do not force the player to kill. Only if the player "
    "deliberately recovers a body they are sure is dead, propose recover_body."
)
RECOVERED_TEXT = (
    "The player carries a body out of the fissure. Every dead human must be "
    "burned: an unburned corpse can be studied or puppeted. Carry it to the "
    "Great Pyres. Propose cremate_body only after the player has actually "
    "put the body into the fire, never merely on arriving there."
)
CREMATED_TEXT = (
    "The pyres burn. The Council owes the player its bounty. Describe the "
    "ashes; the game pays the reward when the player claims it."
)
REWARDED_TEXT = "The Council is grateful in its grim way. The bounty is closed."


def _stage(index: int, stage: str, text: str, place: str | None) -> Cond:
    stage_check = eq(RETRIEVAL, stage)
    when = stage_check if place is None else all_of(stage_check, at(place))
    return Cond(label("R", index, f"bounty {stage}"), when, (), text, is_fact=True)


def retrieval_conditions() -> list[Cond]:
    return [
        _stage(1, "offered", OFFERED_TEXT, "council_hall"),
        _stage(2, "accepted", ACCEPTED_TEXT, None),
        _stage(3, "accepted", SHAFT_TEXT, "fissure_depths"),
        _stage(4, "body_recovered", RECOVERED_TEXT, None),
        _stage(5, "cremated", CREMATED_TEXT, None),
        _stage(6, "rewarded", REWARDED_TEXT, None),
    ]
