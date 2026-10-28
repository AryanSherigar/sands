import type { CardKind } from "../types/card.types";
import type { GuideQuestion, QuestionGroup } from "../types/guide.types";

const ask = (
  id: string,
  label: string,
  prompt: string,
  pick?: GuideQuestion["pick"],
): GuideQuestion => ({ id, label, prompt, ...(pick ? { pick } : {}) });

const group = (
  id: string,
  name: string,
  questions: GuideQuestion[],
): QuestionGroup => ({ id, name, questions });

export const PREMISE_QUESTION_GROUPS: QuestionGroup[] = [
  group("premise", "Your story", [
    ask("want", "What they want", "What do they want?"),
    ask("stakes", "What stands in their way?", "What stands in their way?"),
    ask("fail", "If they fail", "What happens if they fail?"),
  ]),
];

export const PLAYER_QUESTION_GROUPS: QuestionGroup[] = [
  group("player", "About the player", [
    ask("looks", "Looks", "Looks"),
    ask("background", "Background", "Background"),
    ask("good-at", "Good at", "What are they good at?"),
    ask("wants", "Wants", "What do they want?"),
    ask("carries", "Carries", "What do they carry?"),
    ask("unknown", "Doesn't know yet", "What don't they know yet?"),
  ]),
];

export const OPENING_QUESTION_GROUPS: QuestionGroup[] = [
  group("opening", "The first moment", [
    ask("opening-where", "Where", "Where is the player, exactly?"),
    ask("opening-just-happened", "What just happened", "What just happened?"),
    ask("opening-senses", "What they sense", "What can they see, hear or smell right now?"),
    ask("opening-who", "Who else is here", "Who else is here?", {
      kind: "character",
      predicate: "is here at the start",
    }),
    ask("opening-demands", "What demands attention", "What demands their attention first?"),
    ask("opening-knows", "What they know", "What does the player know and not know yet?"),
  ]),
];

export const STYLE_QUESTION_GROUPS: QuestionGroup[] = [
  group("style", "How it is told", [
    ask("style-teller", "Who tells it", "Who is telling the story: an unseen narrator, or a character?"),
    ask("style-you", "Calling the player", 'Should it call the player "you"?'),
    ask("style-length", "Reply length", "How long should each reply be?"),
    ask("style-pace", "Describe or move on", "How much should it describe vs. move the story on?"),
    ask("style-fairness", "How fair", "How fair or harsh should the world be?"),
    ask("style-never", "Never do", "What should the narrator never do?"),
  ]),
];

export const CHARACTER_QUESTION_GROUPS: QuestionGroup[] = [
  group("looks", "Looks", [
    ask("age", "Age", "How old are they?"),
    ask("first-notice", "First impression", "What do people notice first?"),
    ask("wears", "Wears and carries", "What do they usually wear or carry?"),
  ]),
  group("personality", "Personality", [
    ask("three-words", "Three words", "Three words that describe them."),
    ask("good-at", "Good at", "What are they good at?"),
    ask("flaw", "Flaw", "What's their flaw?"),
    ask("quirk", "Habit or quirk", "Any habit or quirk?"),
  ]),
  group("voice", "Voice", [
    ask("voice", "Voice", "How do they talk?"),
    ask("one-line", "A line they'd say", "Write one line they'd say."),
    ask("phrase", "Favourite phrase", "Any word or phrase they always use?"),
  ]),
  group("wants-fears", "Wants & fears", [
    ask("want", "Wants", "What do they want?"),
    ask("why", "Why", "Why?"),
    ask("fear", "Afraid of", "What are they afraid of?"),
    ask("secret", "Secret", "What's their secret?"),
  ]),
  group("with-player", "With the player", [
    ask("treat", "At first", "How do they treat the player at first?"),
    ask("trust", "Earning trust", "What makes them trust the player more?"),
    ask("turn", "Turning against", "What would turn them against the player?"),
    ask("never", "Would never", "What would they never do?"),
  ]),
  group("history", "History", [
    ask("before", "Before the story", "What happened to them before the story?"),
    ask("matters", "Matters to them", "Who matters to them?", {
      kind: "any",
      predicate: "cares about",
    }),
  ]),
  group("knows", "What they know", [
    ask("knows", "Knows", "What do they know that the player needs?"),
    ask(
      "wont-tell",
      "Won't tell",
      "What will they never tell, and what would make them tell?",
    ),
  ]),
  group("where", "Where", [
    ask("found-at", "Usually found at", "Where can the player usually find them?", {
      kind: "place",
      predicate: "is usually found at",
    }),
  ]),
  group("change", "How they change", [
    ask("change", "By the end", "How might they be different by the end?"),
  ]),
];

export const WORLD_QUESTION_GROUPS: QuestionGroup[] = [
  group("time-place", "Time & place", [
    ask("setting", "Setting", "Where is it set?"),
    ask("era", "When", "When?"),
    ask("land", "Land and weather", "What's the land or the weather like?"),
    ask("reach", "How far you can go", "How far can the player go?"),
  ]),
  group("everyday", "Everyday life", [
    ask("normal", "What's normal", "What's normal here that would surprise an outsider?"),
    ask("living", "Ordinary life", "How do ordinary people live?"),
    ask("beliefs", "Beliefs", "What do they believe?"),
    ask("technology", "Technology", "How advanced is the technology?"),
  ]),
  group("power", "Power", [
    ask("in-charge", "In charge", "Who's in charge?"),
    ask("powerless", "No power", "Who has no power?"),
    ask("laws", "Laws", "What are the laws?"),
    ask("conflict", "Who's fighting", "Who's fighting whom?"),
  ]),
  group("danger", "Danger", [
    ask("threats", "Threats", "What threatens people?"),
    ask("forbidden", "Forbidden", "What's forbidden?"),
    ask("breakers", "Breaking the rules", "What happens to people who break the rules?"),
  ]),
  group("special-rules", "Special rules", [
    ask("special", "Special rules", "Is there magic, technology or a curse?"),
    ask("how", "How it works", "How does it work?"),
    ask("cost", "What it costs", "What does it cost?"),
    ask("who", "Who can use it", "Who can use it?"),
  ]),
  group("history", "History", [
    ask("big-event", "Before the story", "What big thing happened before the story?"),
    ask("legends", "Legends", "What legends do people tell?"),
    ask("forgotten", "Forgotten", "What has everyone forgotten?"),
  ]),
  group("senses", "Senses & mood", [
    ask("senses", "Looks, sounds, smells", "What does it look, sound and smell like?"),
    ask("images", "Recurring images", "What images keep coming back?"),
  ]),
  group("secrets", "Secrets", [
    ask("truth", "The hidden truth", "What's true that most people don't know?"),
  ]),
];

const PLACE_QUESTION_GROUPS: QuestionGroup[] = [
  group("senses", "Senses", [
    ask("looks", "Looks", "What does it look like?"),
    ask("sounds", "Sounds", "What does it sound like?"),
    ask("smells", "Smells", "What does it smell like?"),
    ask("feel", "Warm, cold or damp", "Is it warm, cold or damp?"),
  ]),
  group("people", "People", [
    ask("here", "Usually here", "Who is usually here?", {
      kind: "character",
      predicate: "is usually home to",
    }),
    ask("guards", "Owned or guarded by", "Who owns or guards it?", {
      kind: "any",
      predicate: "is guarded by",
    }),
  ]),
  group("getting-there", "Getting there", [
    ask("where", "Where it is", "Where is it?", { kind: "place", predicate: "is near" }),
    ask("entry", "Getting in", "How do you get in?"),
    ask("blocked", "In the way", "Is anything in the way?"),
  ]),
  group("secrets", "Secrets", [
    ask("hidden", "Hidden here", "What's hidden here?"),
    ask("happened", "What happened here", "What happened here before?"),
  ]),
  group("mood", "Mood", [
    ask("feel-here", "How it should feel", "How should the player feel here?"),
    ask("changes", "Over time", "Does it change at night or over time?"),
  ]),
];

const GROUP_QUESTION_GROUPS: QuestionGroup[] = [
  group("purpose", "Purpose", [
    ask("want", "Wants", "What do they want?"),
    ask("believe", "Believes", "What do they believe?"),
  ]),
  group("people", "People", [
    ask("leader", "Led by", "Who leads them?", { kind: "character", predicate: "is led by" }),
    ask("members", "Members", "Who are their members?", {
      kind: "character",
      predicate: "has member",
    }),
  ]),
  group("behaviour", "Behaviour", [
    ask("outsiders", "Toward outsiders", "How do they treat outsiders?"),
    ask("player", "Toward the player", "How do they treat the player at first?"),
    ask("help-hunt", "Help or hunt", "What would make them help or hunt the player?"),
  ]),
  group("reputation", "Reputation", [
    ask("known-for", "Known for", "What are they known for?"),
    ask("enemies", "Enemies", "Who are their enemies?"),
  ]),
  group("secrets", "Secrets", [
    ask("hide", "Hidden", "What do they hide even from members?"),
  ]),
];

const THING_QUESTION_GROUPS: QuestionGroup[] = [
  group("looks", "Looks", [
    ask("looks", "Looks", "What does it look like?"),
    ask("marks", "Marks or sounds", "Any marks or sounds?"),
  ]),
  group("power", "Power", [
    ask("does", "What it does", "What does it do?"),
    ask("cost", "What using it costs", "What does using it cost?"),
  ]),
  group("ownership", "Ownership", [
    ask("holder", "Held by", "Who has it now?", { kind: "character", predicate: "is held by" }),
    ask("wanted-by", "Wanted by", "Who wants it?"),
  ]),
  group("meaning", "Meaning", [ask("matters", "Why it matters", "Why does it matter?")]),
];

const NO_QUESTION_GROUPS: QuestionGroup[] = [];

const QUESTION_GROUPS_BY_KIND: Record<CardKind, QuestionGroup[]> = {
  character: CHARACTER_QUESTION_GROUPS,
  place: PLACE_QUESTION_GROUPS,
  group: GROUP_QUESTION_GROUPS,
  thing: THING_QUESTION_GROUPS,
  other: NO_QUESTION_GROUPS,
};

export const getQuestionGroupsForCard = (
  kind: CardKind,
  isPlayer: boolean,
): QuestionGroup[] => (isPlayer ? PLAYER_QUESTION_GROUPS : QUESTION_GROUPS_BY_KIND[kind]);
