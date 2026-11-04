"""Group T: the Grand Tithe, a hidden five-stage arc driven by intent markers.

Each transition is legal only from the previous stage, so the order is enforced
by the condition expressions and not by the narrator. The secret is told to the
narrator only from the stage that has earned it.
"""

from scripts.seeding.expr import SET, Cond, Mut, all_of, eq, ne
from scripts.zegaris.conditions.common import TITHE, TITHE_STEP, clear, label

HIRED_TEXT = (
    "The Magistrate has hired the player to haul a 'Sacred Relic of the First "
    "Covenant' across the mountain road when the Grand Tithe comes. Be warm, "
    "formal and condescending. He never touches the player and never says "
    "anything false: he omits. The relic must never be opened or looked into. "
    "Offer the player a worker's badge at the Gate of the Un-Sworn; when "
    "you hand it over, end your reply with a final line [INTENT: access_step=badge]."
)
HAULING_TEXT = (
    "The player takes the traces of a heavy, iron-plated black carriage, "
    "escorted by silent Black Templars. The magistrates call any weeping or "
    "voices inside 'holy resonances'. Describe the weight, the road and the "
    "silence. The Templars never speak, even to answer a question. Do not "
    "say what is inside and do not explain the sounds."
)
ECLIPSE_TEXT = (
    "The eclipse nears totality. Strike the player with overwhelming, "
    "suffocating grief, weeping and cold terror leaking through the iron "
    "seams. The player now knows, beyond doubt, that living children are "
    "inside. Do not decide what the player does next."
)
AFTERMATH_TEXT = (
    "The player has taken the twins from the carriage. From this moment "
    "Zegaris turns on them. Let the world react, but do not end the story and "
    "do not choose a destination for the player."
)
OFFERED_FACT = (
    "Zegarian magistrates have ridden up to the crossroads to recruit newly "
    "arrived outlanders with no ties here to haul a sacred carriage for the "
    "Grand Tithe. They will not touch or sit near an outsider, but they are "
    "recruiting: if the player offers to work, the eldest answers coolly and "
    "precisely, states the pay in gold and that they will be sent to the "
    "Magistrate at the Gate of the Un-Sworn, and never says what the cargo is. "
    "When the player agrees to the job, end your reply with a final line "
    "[INTENT: tithe_step=hired]."
)
HIRED_FACT = (
    "The player is bonded to the Tithe. Carry the lie that the cargo is a "
    "sacred relic. Zegarians keep their word to the letter and hide the rest."
)
HAULING_FACT = (
    "Hauling the black carriage. Templars flank it in silence. Keep the sounds "
    "from inside ambiguous until the eclipse. Foreshadow only: cold, a "
    "hum, the Templars' unease."
)
ECLIPSE_FACT = (
    "THE TRUTH (reveal only through what the player perceives). Inside the "
    "carriage are two children with golden eyes: the twins of the Sun "
    "Priestess whom Zegaris betrayed centuries ago. They cannot age, heal or "
    "die, and for three hundred years they have absorbed the city's sickness "
    "while staring into the face of the god that took their mother. Taken as "
    "newborns, they have never known trust, warmth or hope. They can speak, "
    "but they do not refuse rescue: they do not know what rescue is. Opening "
    "the carriage finds two hollow, immortal vessels in agony, not relatable "
    "children waiting to be saved. The Templars are not human: low, faceless "
    "entities summoned from Zegarim's realm. The player may open the "
    "carriage, keep hauling, walk away or confront the magistrates; resolve "
    "each honestly with no rescue guarantee. If the player deliberately "
    "opens the carriage and takes the twins away, end your reply with a "
    "final line [INTENT: tithe_step=aftermath]."
)
AFTERMATH_FACT = (
    "Zegaris hunts the player. Templars are faceless entities that do not "
    "tire; citizens are shocked, not cruel. Striking a Zegarian is a crime "
    "the city punishes with slavery, but the city now wants the twins back "
    "more than a slave. The twins follow because they know nothing else. "
    "Play them as hollow and unfamiliar with kindness. The player may go "
    "anywhere. Never narrate an ending."
)


def _transition(
    index: int, name: str, previous: str, following: str, text: str
) -> Cond:
    return Cond(
        label(
            "T",
            index,
            f"{previous} to {following}",
        ),
        all_of(eq(TITHE_STEP, name), eq(TITHE, previous)),
        (Mut(TITHE, SET, following), clear(TITHE_STEP)),
        text,
    )


def _stage_fact(index: int, stage: str, text: str) -> Cond:
    return Cond(
        label("T", index, f"{stage} truth"), eq(TITHE, stage), (), text, is_fact=True
    )


def tithe_conditions() -> list[Cond]:
    return [
        _transition(1, "hired", "offered", "hired", HIRED_TEXT),
        _transition(2, "hauling", "hired", "hauling", HAULING_TEXT),
        _transition(3, "eclipse", "hauling", "eclipse", ECLIPSE_TEXT),
        _transition(4, "aftermath", "eclipse", "aftermath", AFTERMATH_TEXT),
        Cond(
            label("T", 10, "offered briefing"),
            eq(TITHE, "offered"),
            (),
            OFFERED_FACT,
            is_fact=True,
        ),
        _stage_fact(5, "hired", HIRED_FACT),
        _stage_fact(6, "hauling", HAULING_FACT),
        _stage_fact(7, "eclipse", ECLIPSE_FACT),
        _stage_fact(8, "aftermath", AFTERMATH_FACT),
        Cond(
            label("T", 9, "discard out-of-order step"),
            ne(TITHE_STEP, ""),
            (clear(TITHE_STEP),),
            "",
        ),
    ]
