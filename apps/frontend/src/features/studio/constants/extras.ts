import type { ToolKey } from "@/shared/constants/scenario-tools";

export type ExtraId = "map" | "music" | "minigames" | "atmosphere" | "rule_sheet" | "rule_checks";

export interface ExtraDefinition {
  id: ExtraId;
  name: string;
  description: string;
  tool: ToolKey | null;
}

type ExtraRemovalState = "checking" | "in_use" | "free";

export interface ExtraRemoval {
  toolName: string;
  state: ExtraRemovalState;
}

export const EXTRA_TAB_PREFIX = "extra-";

export const EXTRAS: readonly ExtraDefinition[] = [
  {
    id: "map",
    name: "Map",
    description: "Let players see where they are. Uses your Places.",
    tool: null,
  },
  {
    id: "music",
    name: "Mood music",
    description: "Music that follows the story's mood.",
    tool: null,
  },
  {
    id: "minigames",
    name: "Minigames",
    description: "Short challenges inside the story.",
    tool: null,
  },
  {
    id: "atmosphere",
    name: "Atmosphere",
    description: "Sound cues and effects on the page.",
    tool: "atmosphere",
  },
  {
    id: "rule_sheet",
    name: "Rule sheet",
    description: "A list of rules the player carries. It can change.",
    tool: "rule_sheet",
  },
  {
    id: "rule_checks",
    name: "Rule checks",
    description: "Timed prompts and memory tests for the player.",
    tool: "rule_checks",
  },
];

export const EXTRA_ON_LABEL = "On";
export const EXTRA_ADD_LABEL = "Add";
export const EXTRA_EDIT_LABEL = "Edit";
export const EXTRA_REMOVE_LABEL = "Remove";
export const EXTRA_BACK_LABEL = "Back to Extras";
export const EXTRA_SWITCH_FAILED_MESSAGE = "Couldn't change that extra. Try again.";
export const EXTRA_STILL_USED_MESSAGE = "Something else in your story still uses it, so it stays on.";
export const EXTRA_KEPT_MESSAGE = "What you made is kept but switched off. Add it again anytime to use it.";
export const EXTRA_TURN_OFF_LABEL = "Turn off";
export const EXTRA_CANCEL_LABEL = "Cancel";
export const EXTRA_ACKNOWLEDGE_LABEL = "OK";

export const formatExtraTurnOffQuestion = (toolName: string): string => `Turn off ${toolName} too?`;
export const formatExtraNeedsAdvanced = (extraName: string): string =>
  `Turn Advanced mode on to use ${extraName}.`;
