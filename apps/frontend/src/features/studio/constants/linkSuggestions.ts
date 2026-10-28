import type { CardKind } from "../types/card.types";

export const LINK_SUGGESTIONS: Record<string, string[]> = {
  "character>place": ["lives in", "works at", "is hiding in", "is afraid of"],
  "character>character": [
    "is the sister of",
    "loves",
    "owes money to",
    "betrayed",
  ],
  "character>group": ["leads", "belongs to", "is hunted by"],
  "character>thing": ["owns", "is looking for", "stole"],
  "place>place": ["is inside", "is next to", "leads to"],
  "thing>place": ["is hidden in"],
};

export const FALLBACK_LINK_SUGGESTIONS: string[] = ["is connected to"];

export const buildSuggestionKey = (
  subjectKind: CardKind,
  objectKind: CardKind,
): string => `${subjectKind}>${objectKind}`;
