import type { StateMutationOp } from "@/shared/types/stateMutation.types";
import type { Comparison } from "../types/sentence.types";

export const NEW_RULE_LABEL = "New rule";
export const RULE_LABEL_MAX_LENGTH = 255;
export const MAX_RULE_CHANGES = 16;
export const SOUND_ENABLE_FAILED_MESSAGE = "Couldn't switch on sound cues. Try again.";
export const EVERY_TURN_LABEL = "Every turn while this is true";
export const ONLY_ONCE_LABEL = "Only once, the first time";
export const EVERY_TURN_HELP =
  "Every turn keeps applying — a rule that lowers Sanity will lower it every turn until the condition stops being true.";
export const DEFAULT_SOUND_SILENCE_MS = 800;

export const CHANGE_OP_LABELS: Record<StateMutationOp, string> = {
  set: "set to",
  increment: "goes up by",
  decrement: "goes down by",
};

export interface RuleExample {
  id: string;
  label: string;
  title: string;
  isOneShot: boolean;
  when: { valueLabel: string; comparison: Comparison; amount?: number | string };
  instruction?: string;
  change?: { valueLabel: string; op: StateMutationOp; amount: number };
}

export const RULE_EXAMPLES: readonly RuleExample[] = [
  {
    id: "trust-secret",
    label: "When Trust is at least 8 → Tell the narrator: Mara shares her secret",
    title: "When Trust is at least 8",
    isOneShot: false,
    when: { valueLabel: "Trust", comparison: "at_least", amount: 8 },
    instruction: "Mara shares her secret.",
  },
  {
    id: "night-health",
    label: "When Time becomes Night → Health goes down by 1 each turn",
    title: "When Time becomes Night",
    isOneShot: false,
    when: { valueLabel: "Time", comparison: "becomes_option", amount: "Night" },
    change: { valueLabel: "Health", op: "decrement", amount: 1 },
  },
  {
    id: "key-door",
    label: "Only once, when Has the key becomes yes → Tell the narrator: the lighthouse door unlocks",
    title: "When Has the key becomes yes",
    isOneShot: true,
    when: { valueLabel: "Has the key", comparison: "becomes_yes" },
    instruction: "The lighthouse door unlocks.",
  },
];

export const CUSTOM_TITLE_METADATA_KEY = "custom_title";
export const AUTHORED_EFFECT_METADATA_KEYS = ["client_effect", "authored_image_url"] as const;
