import type { ActionBlock } from "./assistant.types";

export type ScopedSlotId =
  | "title"
  | "logline"
  | "premise"
  | "world_lore"
  | "opening"
  | "style"
  | "card_lore";

export type ScopedProposalState = "pending" | "applied" | "dismissed";

export type ScopedWriteMode = "replace" | "append";

export interface ScopedChatContext {
  oneLineIdea: string;
  tabKind: string;
  tabLabel: string;
  tabText: string;
}

export interface ScopedProposal {
  label: string;
  before: string;
  after: string;
  canApply: boolean;
  reason: string | null;
}

export interface ScopedTabBinding {
  context: ScopedChatContext;
  describeProposal: (block: ActionBlock) => ScopedProposal;
  applyProposal: (block: ActionBlock, mode: ScopedWriteMode) => Promise<void>;
}

export type ScopedTab =
  | { kind: "none" }
  | { kind: "guide"; stepId: string | null }
  | { kind: "card"; entityId: string }
  | { kind: "playtest" }
  | { kind: "feature"; featureId: string };
