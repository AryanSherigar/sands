import type { ActionTarget } from "../types/assistant.types";
import type { ScopedSlotId } from "../types/scopedChat.types";
import type { GuideStepId } from "./guideSteps";

export const SCOPED_TAB_TEXT_MAX_CHARS = 8000;
export const SCOPED_CHAT_WELCOME =
  "Hi. I can see the tab you have open and your one line idea. Ask me for ideas and I will suggest changes you can accept or dismiss.";
export const SCOPED_EMPTY_TAB_NOTE = "This tab is empty, so Chat only sees your one line idea.";
export const SCOPED_NEW_CHAT_LABEL = "New chat";
export const SCOPED_APPEND_SEPARATOR = "\n\n";

type TargetSlots = Partial<Record<ActionTarget, ScopedSlotId>>;

export const GUIDE_STEP_TARGET_SLOTS: Record<GuideStepId, TargetSlots> = {
  idea: { title: "title", logline: "logline" },
  premise: { conflict: "premise" },
  player: {},
  characters: {},
  world: { lore: "world_lore" },
  opening: { opening_prompt: "opening", style: "style", instructions: "style" },
  endings: {},
  tracked_values: {},
  rules: {},
  hard_limits: {},
  extras: {},
  finish: {},
};

export const EDITOR_TARGET_SLOTS: TargetSlots = {
  title: "title",
  logline: "logline",
  conflict: "premise",
  lore: "world_lore",
  opening_prompt: "opening",
  style: "style",
  instructions: "style",
};

export const CARD_TARGET_SLOTS: TargetSlots = {
  lore: "card_lore",
  story_card: "card_lore",
};

export const TARGET_HOME_LABELS: Partial<Record<ActionTarget, string>> = {
  title: "the Idea step",
  logline: "the Idea step",
  conflict: "the Premise step",
  lore: "the World step or a card",
  story_card: "a card",
  opening_prompt: "the Opening step",
  style: "the Opening step",
  instructions: "the Opening step",
};

export const SLOT_LABELS: Record<ScopedSlotId, string> = {
  title: "Name",
  logline: "One line idea",
  premise: "Premise",
  world_lore: "World",
  opening: "Opening",
  style: "Storytelling style",
  card_lore: "Card",
};
