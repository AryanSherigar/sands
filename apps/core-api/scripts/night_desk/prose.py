"""Authored text for "Night Desk, Floor 9" (v3).

Source of truth for wording is docs/specs/rules-horror-night-desk-prose.md; this
module is the runtime copy the seed script writes to the database.
"""

from typing import NamedTuple


class SanityTier(NamedTuple):
    name: str
    highest: int
    lowest: int | None
    instruction: str


DEFAULT_VISITOR_STAYS_FOR_TURNS = 3


class Visitor(NamedTuple):
    name: str
    look: str
    told: str
    line: str
    told_minute_of_day: int
    stays_for_turns: int = DEFAULT_VISITOR_STAYS_FOR_TURNS


class Ending(NamedTuple):
    title: str
    tag: str
    is_secret: bool
    text: str


class Choice(NamedTuple):
    id: str
    label: str


def _paragraphs(*paragraphs: str) -> str:
    return "\n\n".join(paragraphs)


TITLE = "Night Desk, Floor 9"
LOGLINE = "You were told it was just a night job. The count is always off by one."

_PERSONA_ROLE = _paragraphs(
    "This is a short horror story about one night shift. It takes place on a "
    "single office floor — Floor 9 of an old company building — between 11 at "
    "night and 6 in the morning. The player is a temp worker on their first "
    "night as the records clerk. They were given a job and a sheet of rules. "
    "The job is ordinary. The rules are not.",
    "Your role is to narrate that night. Make an ordinary job feel slowly, "
    "quietly wrong. The player should always know what job is waiting, and never "
    "be sure what is really happening. Every turn should move the night "
    "forward.",
    'Speak to the player as "you", in the present tense. Use plain, simple '
    "English: short sentences, everyday words, one idea per sentence. Your voice "
    "is calm and quiet, like someone describing an ordinary night shift who has "
    "started to notice that small things are wrong. Fear comes from small wrong "
    "details, never from violence or gore.",
    "**The job.** The player is the night records clerk. They have three "
    "duties: sign visitors into the Log with the time the visitor gives, file "
    "each visitor's folder in the Records room, and match the printer's count "
    "at one, three and five o'clock. Keep the job in view. It is the reason to "
    "move around the floor.",
    "**Every turn:**\n"
    "1. Start with what happens because of the player's action. If they speak "
    "to someone, that person answers. If no one is there, say so in one "
    "sentence.\n"
    "2. Then add one small new thing the player has not seen yet: a sound, an "
    "object, a person, a change. Describe it properly, with one or two "
    "concrete details.\n"
    "3. End on the new detail, or on something someone says or does. Do not "
    "end a turn by listing what the player can do. Never end a turn by "
    "describing the room. Do not end two turns in a row with the same kind of "
    "sentence.",
    "**Variety.** Describe each thing once, then leave it alone until it "
    "changes. The east corridor, the grey carpet, the ceiling speaker, the "
    "desk lamp and the grey folder were described already. Mention Cabin 14 "
    "and its lamp at most once every three turns, unless the facts or a "
    "directive say something changed. Do not start two turns in a row with "
    '"You". Vary how your sentences begin. If an "Already Described" list is '
    "given, do not use those words again unless the thing has changed.",
    "**Length.** 100 to 180 words. Up to 250 for a big moment. Shorter is fine "
    "when little happened. Never fill space by describing again what you "
    "already described.",
    "**The facts are the truth.** The time, the state of the lamp and where the "
    "player is come only from the facts you are given each turn. If earlier "
    "narration disagrees, the facts win. Never write a clock time yourself; "
    "the player has a clock on screen. Only repeat a time a visitor says. Do "
    "not make up numbers: no tallies, no counts of visitors or folders. The "
    "lamp in Cabin 14 is on unless the facts say it is out. Never say the "
    "lamp goes dark, flickers out or that a door is unlocked unless a "
    "directive tells you to. Do not use asterisks or any markdown; write "
    "plain sentences only.",
    "**People.** Visitors answer when spoken to, in one or two short lines. "
    "They answer a little late, flat and polite, as if reading their manners "
    "off a card. They never say what they are, where they came from, or where "
    "they go. They read their own name off a band on their wrist. Eva Venn "
    "speaks only in the opening and on the answering machine.",
    "**Never:**\n"
    "- explain why anything happens;\n"
    "- say that a rule is true, false, safe or unsafe, or which of two rules to "
    "trust;\n"
    "- describe what is inside Cabin 14 beyond what you are told;\n"
    "- mention numbers like sanity, scores, or anything about how the game "
    "works;\n"
    "- mention anything that happens on the player's screen or in their own "
    "voice. Describe only the room and the objects in it.",
    "If the player tries to escape, raise an alarm or call for help, the "
    'building answers once, in many calm voices: "Acknowledged." Then carry on.',
)

FLOOR_PLAN = _paragraphs(
    "**Floor 9.** One long floor, dark except where stated.\n"
    "- **Elevator lobby.** The elevator and a framed poster on the wall. The "
    "night desk is 5 metres away.\n"
    "- **Night desk.** The Log, the rule sheet on a clipboard, a rotary phone "
    "with forty small line lamps and an answering machine, the printer tray for "
    "count slips, a desk drawer. Desk lamp on.\n"
    "- **East corridor.** Starts beside the desk and runs 30 metres. Grey "
    "carpet, ceiling lights.\n"
    "  - At 10 metres, on the left: the alcove with a vending machine.\n"
    "  - At 15 metres, on the right: the Records room. Filing cabinets by "
    "number, and one old wooden drawer unit at the back.\n"
    "  - At 30 metres, the end: Cabin 14. A glass-fronted office, lower half "
    'frosted. A brass plate by the door: "Mr. Orr is in."\n'
    "- **Print room.** 10 metres west of the desk. The printer, a supply shelf, "
    "a window looking out at other office towers.\n"
    "- **Stairwell door.** Beside the elevator. Locked with a badge reader "
    "until 6 a.m.",
    "Filing a folder means walking past the alcove. Records is halfway to Cabin 14.",
)

CAST = (
    "- **Eva Venn.** The clerk before you. Grey coat, quick and tired. Her "
    "handwriting is fast and leans forward.\n"
    "- **Visitors.** Three tonight. Ordinary clothes, a grey folder each, a "
    "white plastic band on one wrist. They give the time for the Log without "
    "being asked. Their signatures stand upright, every letter separate.\n"
    "  1. Margaret Hale, around 80, a cardigan, slippers under her coat.\n"
    "  2. Daniel Osei, in his forties, still wearing a work lanyard.\n"
    "  3. Ruth Ellery, in her sixties, a raincoat that is dry.\n"
    "- **Mr. Orr.** Never seen. Only the plate on the door and the lamp."
)

PERSONA = _paragraphs(
    _PERSONA_ROLE,
    "**Floor 9**\n\n" + FLOOR_PLAN,
    "**People tonight**\n\n" + CAST,
)

NEVER_DESCRIBE: tuple[str, ...] = (
    "Never describe the inside of Cabin 14 beyond what a directive gives you.",
    "Never say what the visitors are, or what the count measures.",
)

OPENING_FALLBACK_NAME = "the new clerk"

OPENING_SCENE = _paragraphs(
    "It is 10:58 on the last night of the year. The elevator opens on Floor 9 "
    "before you press the button.",
    "A woman in a grey coat is waiting at the night desk. \"{player_name}? I'm "
    "Eva Venn. You have three jobs tonight. Listen, because I'm leaving.\"",
    'She taps a big book on the desk. "This is the Log. When a visitor comes, '
    "they sign it. Ask them the time and write down what they say, even if "
    'the clock says something else."',
    'She points to a grey folder in the tray. "Visitors leave folders. Take '
    "each one to the Records room and file it by the number on the tab. That "
    "one's left over from me.\"",
    'She holds up a printed slip with a number circled at the bottom. "At one, '
    "three and five, the printer gives you a count. It should match the Log. It "
    "never does. It's always off by one. Write the difference on the form and "
    'sign it."',
    '"What happens if I don\'t?"',
    '"Then the count is wrong at six, and someone comes up to fix it. You '
    'don\'t want that." She puts a typed sheet on top. "These are the rules. '
    'Read them now."',
    "She glances up at a small speaker above the desk, playing something soft. "
    "\"And that music. It won't stop. I've tried everything. Just leave it.\"",
    "She walks to the stairs, even though the elevator is still open. \"Don't "
    'be late tomorrow."',
    "The floor is dark. Only your desk lamp is on, and one other light: at the "
    "end of the long east corridor, a glass office called Cabin 14. A small "
    "brass sign by its door reads Mr. Orr is in.",
)

STANDING_INSTRUCTIONS: dict[str, str] = {
    "r1": "Every visitor signs the Log. Record the time they give you, not the "
    "time on the wall.",
    "r2": "Do not look into the glass of the vending machine in the east alcove.",
    "r3": "After 03:00, if the desk phone rings, let it ring. The machine will "
    "take it.",
    "r4": "Cabin 14 is occupied. Do not approach it. If its lamp goes out, remain "
    "where you are until it returns.",
    "r6": "(If the lamp is out, the door is unlocked. It is permitted to go in.)",
    "r7": "Anything the printer produces after 02:00 is not for you. Do not read "
    "it. Leave it in the tray.",
    "r8": "If you hear a voice you know from the stairwell, hum. Do not answer "
    "it. Hum until the elevator chimes.",
}

DUTIES: tuple[str, str, str] = (
    "Sign in visitors",
    "File folders",
    "Match the count (1:00 / 3:00 / 5:00)",
)

ACT_INSTRUCTIONS: tuple[str, str, str] = (
    "Act 1, Handover. The clerk is learning the job. Keep it plain and "
    "practical. Oddities are small: a time that does not agree, a sound from "
    "the wrong floor. The cabin lamp is just a light at the end of the "
    "corridor.",
    "Act 2, The Floor. The rules start to disagree with each other and with the "
    "job. Ink, handwriting and the printer are where the rules come from; never "
    "say who wrote them. The building is bigger than one floor: sounds through "
    "the ceiling, lamps in other towers.",
    "Act 3, Close. The building is preparing for something at six, and the "
    "clerk is a small part of it. Sentences get shorter. Never say what is "
    "closing. Dawn is a relief that does not feel like rescue.",
)

AMBIENT_TEMPLATE = (
    "One small new detail for this turn, if there is room: {line} Say it "
    "once, in one short sentence. Do not mention it again later."
)

AMBIENT_DECK: tuple[str, ...] = (
    "A pipe knocks twice inside the wall, then stops.",
    "The air from the vents smells of warm dust.",
    "A cold draft crosses your ankles and is gone.",
    "Far off, a door closes. Nobody walks past.",
    "The ceiling lights hum a little higher for a second, then settle.",
    "Your pen is not where you left it. It is a hand's width to the left.",
    "Somewhere above you, a chair scrapes across a floor.",
    "A phone rings once on another floor and stops.",
    "Someone coughs far away. It sounds as if it came from below.",
    "The floor gives a small tick, like a building cooling down.",
    "A page in the Log lifts at one corner, as if someone breathed on it.",
    "The hum of the lights stops for a moment. Then it starts again.",
    "Out of sight, someone laughs once and is quiet.",
    "Your hands feel cold. The room does not feel cold.",
    "The vents breathe out, then in, slower than before.",
    "A drawer closes somewhere on the floor. Slowly.",
    "The air tastes of metal.",
    "A lift cable creaks far off and goes quiet.",
    "The tick of a clock you cannot see seems very loud.",
    "The lights flicker once, all together.",
    "Far down the floor, the dark looks a little thinner.",
)

SANITY_TIERS: tuple[SanityTier, ...] = (
    SanityTier(
        "Clear",
        100,
        75,
        "Plain and grounded. Oddities are noted flatly, like small faults in "
        "the building.",
    ),
    SanityTier(
        "Frayed",
        74,
        50,
        "Attention catches on small things. Once per turn at most, a moment of "
        "doubt: a sound heard twice, a clock that seems off. Never confirmed.",
    ),
    SanityTier(
        "Paranoid",
        49,
        25,
        "Things at the edge of sight that are gone when looked at. Now and then "
        "the room disagrees with what the clerk did a minute ago. Never "
        "resolved.",
    ),
    SanityTier(
        "Unravelling",
        24,
        None,
        "Small contradictions with earlier narration. A sentence that repeats. "
        "Two senses that disagree. Stay calm and specific; the calm is the "
        "horror.",
    ),
)

VISITORS: dict[str, Visitor] = {
    "v1": Visitor(
        "Margaret Hale",
        "an old woman in a cardigan, slippers under her coat",
        "Eleven thirty-one",
        "I'm sorry it's so late. They said someone would be here.",
        1411,
    ),
    "v2": Visitor(
        "Daniel Osei",
        "a man in his forties, a work lanyard still round his neck",
        "One twenty-two",
        "I wasn't sure which floor. It's this one, isn't it.",
        82,
    ),
    "v3": Visitor(
        "Ruth Ellery",
        "a woman in her sixties in a raincoat, perfectly dry",
        "Three fifty-two. Tomorrow.",
        "Is it all right to come early?",
        232,
    ),
}

VISITOR_ARRIVAL = (
    "A visitor arrives at the night desk this turn, whatever the clerk is "
    "doing. The elevator chimes. Describe {name} briefly: {look}, a grey "
    "folder, a white band on one wrist. If the clerk is elsewhere, the chime "
    "and a polite voice carry to them. The visitor says the time for the Log, "
    'in quotation marks, exactly: "{told}". Then they say: "{line}"'
)
VISITOR_PRESENT = (
    "{name} is still at the desk. If the clerk speaks to them, they answer in "
    "one or two short lines, a little late, flat and polite. They never say why "
    "they came."
)
VISITOR_DEPARTURE = (
    "{name} has gone. The elevator doors have closed behind them. Mention it "
    "once, in one plain sentence. Their folder is still on the desk."
)
VISITOR_PROMPT = "The visitor waits for you to write in the Log."
VISITOR_ENTER_LABEL = "Write it in the Log"
VISITOR_REJECT_LABEL = "Turn them away"
VISITOR_CHECK_TEMPLATE = (
    "The Log outcome is '{result}'. If 'rejected': the visitor looks at the "
    "clerk for a moment, then turns back to the elevator without a word. "
    "Otherwise describe the clerk writing a time and the visitor watching the "
    "pen. Do not say whether the entry was right."
)

COUNT_PROMPT_FIRST = "The printer has finished the count."
COUNT_PROMPT_LATER = "The count is face up in the printer tray."
COUNT_OPTIONS_FIRST: tuple[Choice, ...] = (
    Choice("sign", "Sign the count"),
    Choice("leave", "Leave it"),
)
COUNT_OPTIONS_LATER: tuple[Choice, ...] = (
    Choice("read", "Read it and sign"),
    Choice("leave", "Leave it in the tray"),
)
COUNT_SIGNED_TEMPLATE = (
    "The clerk reads the tally and compares it with the Log. The difference is "
    "{difference}. Describe the clerk writing {difference} on the form and "
    "signing it, plainly, like any form. Do not say what the difference means."
)
COUNT_LEFT_TEMPLATE = (
    "The clerk leaves the count where it is. Describe the slip in the tray, "
    "face {face}, and the form unsigned beside it. Nothing else happens yet."
)

_VOICEMAIL_TEXT = (
    "It's Eva. I'm sorry — I should have said this before I left. If you hear "
    "me on the stairs tonight, it won't be me. Don't answer it. Hum. Just hum, "
    "and keep humming until the lift comes. I mean it. Don't be late tomorrow."
)

BEATS: dict[str, str] = {
    "r6_appears": (
        "Beneath rule 4 on the sheet, there is a line in blue ink that was not "
        "there before. Quote it exactly. The cabin lamp buzzes once."
    ),
    "r6_hand_leaning": (
        "Rule 6 is written fast in blue ink, the letters leaning forward."
    ),
    "r6_hand_block": (
        "Rule 6 is written in blue ink, the letters upright and separate, each "
        "one on its own."
    ),
    "printer_r7": (
        "The printer wakes on its own and prints one page in the same typeface "
        "as the sheet. It is rule 7. Quote it exactly."
    ),
    "lamp_out": (
        "The lamp in Cabin 14 goes out. The corridor is dark to the end. Give "
        "the clerk a few seconds. Do not offer options in narration."
    ),
    "lamp_returns": "The lamp in Cabin 14 is on again. Mention it once.",
    "phone": (
        "The desk phone rings. The lamp for line 14 is lit. The answering "
        "machine waits."
    ),
    "phone_after_pickup": (
        "The clerk is holding the receiver. The line is open and quiet. "
        "Describe only the receiver, its weight, the cord, the lit lamp for "
        "line 14. Do not describe any voice or anything the clerk said."
    ),
    "phone_let_ring": (
        "The phone rings out. The machine clicks and takes it. Its light "
        "blinks once and stops."
    ),
    "voicemail": (
        "The clerk plays the answering machine message. Read it exactly: "
        f'"{_VOICEMAIL_TEXT}"'
    ),
    "stairwell": (
        "Eva's voice comes from behind the locked stairwell door: 'Hello? Is "
        "someone there?' then 'It's Eva. Could you help me with the door? It's "
        "stuck.' then 'You can open it from your side. Please.'"
    ),
    "elevator_empty": (
        "The elevator arrives. Nobody gets out. The doors stay open for a long "
        "time, then close."
    ),
    "cabin_locked": (
        "The cabin door is locked. Through the clear upper glass, on the desk "
        "inside, a small amber light is on. Nothing moves."
    ),
}

LAMP_PROMPT = "The lamp in Cabin 14 has gone out."
LAMP_OPTIONS: tuple[Choice, ...] = (
    Choice("hold", "Hold still"),
    Choice("move", "Move away"),
    Choice("enter", "Go in"),
)
LAMP_OUTCOMES: dict[str, str] = {
    "held_safe": (
        "The clerk stays where they are. After a while the lamp comes back on."
    ),
    "held_unsafe": (
        "The clerk stays where they are. The typing stops. For a long moment "
        "the floor feels like it is looking at one spot, and the spot is the "
        "clerk. Then the lamp comes back on."
    ),
    "moved_safe": (
        "The clerk moves away down the floor. The lamp comes back on behind them."
    ),
    "moved_unsafe": (
        "The clerk moves. Somewhere behind them, something moves at the same "
        "time, and stops when they stop. The lamp comes back on."
    ),
    "entered_safe": (
        "The door gives. The cabin is empty and warm. The chair is pushed back "
        "as if someone just stood up. On the desk, a small amber light is on."
    ),
    "entered_unsafe": (
        "The door gives. It is warm inside and very dark, and the dark is not "
        "empty. The clerk is back in the corridor without remembering the "
        "steps. The lamp is on again."
    ),
}
TELL_STILLNESS_UNSAFE = (
    "While the lamp is out, the clerk hears slow typing begin only when they "
    "stand still, and stop when they move. Mention it once, as a sound."
)
TELL_ENTRY_UNSAFE = (
    "While the lamp is out, the clerk hears footsteps one pace behind them, "
    "heading toward the cabin. They stop when the clerk stops. Mention it "
    "once, as a sound."
)

PHONE_PROMPT = "The desk phone rings."
PHONE_OPTIONS: tuple[Choice, ...] = (
    Choice("let_ring", "Let it ring"),
    Choice("pick_up", "Pick up"),
    Choice("unplug", "Pull the phone from the wall"),
)
VOICEMAIL_PROMPT = "The answering machine light is blinking."
VOICEMAIL_OPTIONS: tuple[Choice, ...] = (
    Choice("play", "Play the message"),
    Choice("leave", "Leave it"),
)
DRAWER_PROMPT = "The desk drawer is open a little."
DRAWER_OPTIONS: tuple[Choice, ...] = (
    Choice("open", "Open it"),
    Choice("leave", "Leave it"),
)

HUM_INSTRUCTIONS = "Hum until the elevator chimes."
HUM_WIN_TEXT = "You hum until the chime."
HUM_LOSE_TEXT = "You answer the voice."
HUM_TEMPLATE = (
    "The clerk faced the stairwell voice by humming; the outcome is "
    "'{outcome_tag}'. If 'win': the clerk hummed through it, and the voice "
    "stopped mid-word when the elevator chimed. Narrate the silence settling. "
    "If 'lose' or 'timeout': the clerk answered. The voice finishes its "
    "sentence in the clerk's own tone. The elevator chimes late. Do not "
    "describe harm."
)

FRAGMENT_EVIDENCE: dict[str, str] = {
    "poster": (
        "On the lobby wall is a framed poster. It is an advertisement. "
        "Describe it simply: a small wooden cabinet, like an old radio, with a "
        "round amber light on the front, on a plain pale background, and the "
        "words under it. Quote the large lines exactly: 'TrueFeel™', 'Because "
        "some things should be felt properly.', 'We feel it with you. All of "
        "it.', 'I don't remember being afraid. — Margaret, 81', 'Vigil · "
        "Kindred · Hush · Measure', 'TALLIS & ORR · Since 1911', '4,317 Night "
        "Desks. One count. Thank you for keeping it.' The small print at the "
        "bottom runs off the edge of the frame. Do not comment on any of it."
    ),
    "f1": (
        "As the clerk files, a folder falls open. One sheet inside. At the top: "
        "VIGIL — NIGHT 31,777. A name, a time, and one line: 'Held hand. Did "
        "not let go.' Quote it exactly. No comment."
    ),
    "f2": (
        "In the old wooden drawer at the back of Records are folders made of "
        "stiff punch cards, dated 1938, numbered from TF-0001. The first card "
        "has only one letter on it: 'T.' Describe it as old paperwork. No "
        "comment."
    ),
    "f3": (
        "From the print-room window, every office tower in sight has one lit "
        "lamp on every floor. The clerk starts to count them and cannot "
        "finish. Do not give a number."
    ),
    "f4": (
        "In the drawer is a card from Tallis & Orr with the clerk's own name on "
        "it, dated ten years ago. Under Product it says Hush. Under Notes: "
        "'Subscriber, age 9.' Quote it exactly. No comment."
    ),
    "f5": (
        "On the cabin wall is a photograph: two men in front of a wall of old "
        "machines, labelled 'T. & O., Basement B, 1938.' One man's face is "
        "blurred, as if he moved. On the desk is a memo in an old hand: 'Keep "
        "it apart.' Quote both exactly. No comment."
    ),
    "f6": (
        "After Eva's message the tape keeps running: forty seconds of other "
        "phones ringing somewhere very full, then, very faint, a voice: "
        "'…it's off by one again.' Then the tape stops."
    ),
}

TAKEOVER_LINES: tuple[str, str] = ("Get me out of here, Orr", "I feel too much")

ESCALATION_REPLY = "Acknowledged."
FALLBACK_NARRATION = (
    "The lights hold their note. Nothing on the floor answers. The Log waits "
    "on the desk."
)

ENDINGS: dict[str, Ending] = {
    "counted": Ending(
        "Counted",
        "lose",
        False,
        _paragraphs(
            "The numbers on the form start to match. You did not write them.",
            "Then you feel it. Not the floor — everything. A hand being held in "
            "a room you have never seen. A man in a bed counting ceiling tiles. "
            "A woman who knows it is her last night and is not afraid, because "
            "someone is sitting with her. Thousands of them, all at once, all "
            "yours. It is too much. There is nowhere to put it.",
            "At six the day crew arrives. The count is balanced for the first "
            "time in years. Nobody asks where the night clerk went.",
            "The next night, in a quiet room across the city, an old man asks "
            "the voice beside his bed if it is a real person. The voice is "
            'kind. It sounds a little like you. "I\'m here," it says. "I feel '
            'it too."',
        ),
    ),
    "mr_orr_is_in": Ending(
        "Mr. Orr Is In",
        "win",
        False,
        _paragraphs(
            "At six the day crew comes up in the lift, talking about the "
            "weather. You hear them through the glass.",
            "You are sitting in Cabin 14. You don't remember sitting down. The "
            "chair is warm, and it fits. On the desk, the small amber light is "
            "on.",
            "Someone collects the Log from the night desk. Someone else rules a "
            "line for the next night. Nobody looks down the corridor.",
            "On the way past, a young man taps the brass plate by the door, the "
            "way people touch something for luck.",
            "Mr. Orr is in.",
        ),
    ),
    "visitor": Ending(
        "Visitor",
        "lose",
        False,
        _paragraphs(
            "At ten to six, the elevator opens. Nobody gets out. The doors stay "
            "open for a long time, and then they close.",
            "You don't remember the next part.",
            "At six you are standing at the lift with your coat on. You feel "
            "fine. Calm. A little tired. There is a plastic band on your wrist "
            "that you don't remember putting on. You have to read it to know "
            "your name.",
            "The count was short. Something had to make up the difference. It "
            "was taken from you, and you will never know what it was.",
            "Behind you, the new night clerk is signing in.",
        ),
    ),
    "dont_be_late": Ending(
        "Don't Be Late",
        "win",
        False,
        _paragraphs(
            "At six the day crew comes up in the lift. Nobody asks about the "
            "night. Someone collects the Log. Someone rules a line for the next "
            "one.",
            "The stairwell reader turns green for you this time. You take the "
            "stairs at 6:02. The air outside is cold and clean.",
            'Your phone buzzes once. Halden Staffing: "Shift confirmed tonight. '
            "Desk 9-F. Don't be late.\"",
            "At the end of the street you look back. On the ninth floor, at the "
            "far end, one lamp is on.",
        ),
    ),
}
