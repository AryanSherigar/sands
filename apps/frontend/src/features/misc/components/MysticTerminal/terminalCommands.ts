import type { TerminalLine } from "../../types/easterEgg.types";
import {
  EASTER_EGG_FACTS,
  getRandomFact,
  searchFacts,
} from "../../data/easterEggFacts";

export const getWelcomeLines = (): TerminalLine[] => [
  {
    id: "welcome-1",
    type: "system",
    content: "✦ SANDS ARCANE TERMINAL v0.4.04 ✦",
  },
  {
    id: "welcome-2",
    type: "system",
    content:
      "You have attuned to the resonance of the void.\nType 'help' or click a quick action below to reveal hidden echoes.",
  },
];

const getHelpContent = (): string =>
  [
    "Available commands:",
    "  anime        - Reveal a sacred anime recommendation",
    "  song         - Summon an echoing musical composition",
    "  fact         - Draw a random fact from the void",
    "  list         - Enumerate all known scrolls and records",
    "  find <text>  - Search the archive by keyword",
    "  roll         - Cast a 1d20 arcane dice check",
    "  clear        - Purge terminal scrollback",
    "  home / back  - Return to the realm of Sands",
  ].join("\n");

const getListContent = (): string => {
  const animeTitles = EASTER_EGG_FACTS.filter((f) => f.category === "anime")
    .map((f) => `  • ${f.title}`)
    .join("\n");
  const songTitles = EASTER_EGG_FACTS.filter((f) => f.category === "song")
    .map((f) => `  • ${f.title}`)
    .join("\n");
  return `[ANIME SCROLLS]:\n${animeTitles}\n\n[RESONATING SONGS]:\n${songTitles}`;
};

const handleRoll = (): TerminalLine => {
  const rollValue = Math.floor(Math.random() * 20) + 1;
  const is_crit_success = rollValue === 20;
  const is_crit_fail = rollValue === 1;

  let outcome = `You rolled a ${rollValue} on 1d20.`;
  if (is_crit_success) {
    outcome += " [NATURAL 20]: An ancient gateway flares with blinding light!";
  } else if (is_crit_fail) {
    outcome += " [CRITICAL FAIL]: The void chuckles at your misfortune.";
  }
  return { id: `roll-${Date.now()}`, type: "system", content: outcome };
};

const handleSearch = (query: string): TerminalLine[] => {
  if (!query) {
    return [
      { id: `err-${Date.now()}`, type: "error", content: "Usage: find <query>" },
    ];
  }
  const results = searchFacts(query);
  if (results.length === 0) {
    return [
      {
        id: `empty-${Date.now()}`,
        type: "error",
        content: `No records found matching "${query}".`,
      },
    ];
  }
  return results.map((fact) => ({
    id: `fact-${fact.id}-${Date.now()}`,
    type: "fact",
    content: fact.title,
    fact,
  }));
};

const handleRandomFact = (
  cmd: "anime" | "song" | "fact",
  timestamp: number,
): TerminalLine[] => {
  const category = cmd === "fact" ? undefined : cmd;
  const fact = getRandomFact(category);
  return [
    { id: `${cmd}-${timestamp}`, type: "fact", content: fact.title, fact },
  ];
};

const handleCoreCommands = (
  lower: string,
  timestamp: number,
): TerminalLine[] | null => {
  if (lower === "help") {
    return [{ id: `help-${timestamp}`, type: "help", content: getHelpContent() }];
  }
  if (lower === "list") {
    return [{ id: `list-${timestamp}`, type: "list", content: getListContent() }];
  }
  if (lower === "roll") {
    return [handleRoll()];
  }
  if (lower === "anime" || lower === "song" || lower === "fact") {
    return handleRandomFact(lower, timestamp);
  }
  return null;
};

export const processCommand = (
  rawInput: string,
  onNavigateHome: () => void,
): TerminalLine[] | "CLEAR" => {
  const trimmed = rawInput.trim();
  const lower = trimmed.toLowerCase();
  const timestamp = Date.now();

  if (lower === "clear") return "CLEAR";
  if (lower === "home" || lower === "back") {
    onNavigateHome();
    return [{ id: `nav-${timestamp}`, type: "system", content: "Returning..." }];
  }
  if (lower.startsWith("find ")) {
    return handleSearch(trimmed.slice(5).trim());
  }

  const handled = handleCoreCommands(lower, timestamp);
  if (handled) return handled;

  return [
    {
      id: `err-${timestamp}`,
      type: "error",
      content: `Unknown rite: "${trimmed}". Type 'help' for known commands.`,
    },
  ];
};
