import type { Comparison } from "../types/sentence.types";

export const NEW_LIMIT_LABEL = "New hard limit";
export const LIMIT_LABEL_MAX_LENGTH = 255;
export const APPLIES_TO_PLAYER = "player";
export const APPLIES_TO_EVERYONE = "global";
export const IN_WORDS_LABEL = "In words";
export const IN_WORDS_HELPER = "The narrator reads this every turn. It is also the reason given when a change is blocked.";
export const ALWAYS_REMEMBER_LINK_LABEL = "Just a rule in words? Add it to Always remember.";
export const EMPTY_COPY = "No hard limits yet. You only need these when one value depends on another.";

export type LimitKind = "compare" | "while";

export const LIMIT_KIND_OPTIONS: Array<{ value: LimitKind; label: string }> = [
  { value: "compare", label: "A value vs another value" },
  { value: "while", label: "While something is true" },
];

interface ExampleRow {
  valueLabel: string;
  comparison: Comparison;
  amount?: number | string;
  refLabel?: string;
}

export interface HardLimitExample {
  id: string;
  label: string;
  text: string;
  kind: LimitKind;
  first: ExampleRow;
  second?: ExampleRow;
}

export const HARD_LIMIT_EXAMPLES: readonly HardLimitExample[] = [
  {
    id: "health-max",
    label: "Health is at most Max health",
    text: "Health can never go above Max health.",
    kind: "compare",
    first: { valueLabel: "Health", comparison: "at_most", refLabel: "Max health" },
  },
  {
    id: "followers-trust",
    label: "Followers is at most Trust",
    text: "Followers can never be more than Trust.",
    kind: "compare",
    first: { valueLabel: "Followers", comparison: "at_most", refLabel: "Trust" },
  },
  {
    id: "chapel-weapon",
    label: "While In the chapel is yes → Weapon drawn must be no",
    text: "While in the chapel, no weapon is ever drawn.",
    kind: "while",
    first: { valueLabel: "In the chapel", comparison: "becomes_yes" },
    second: { valueLabel: "Weapon drawn", comparison: "becomes_no" },
  },
  {
    id: "night-shop",
    label: "While Time is Night → Shop open must be no",
    text: "While it is night, the shop is never open.",
    kind: "while",
    first: { valueLabel: "Time", comparison: "becomes_option", amount: "Night" },
    second: { valueLabel: "Shop open", comparison: "becomes_no" },
  },
];
export const SAY_IT_IN_WORDS_MESSAGE = "Say it in words so the narrator can follow it.";
