import type { ActionMode } from "../../../types/play.types";

export interface FantasyComposerProps {
  tacticalInclinations: string[];
  isNarrating: boolean;
  canRetry: boolean;
  draftInsertion?: { text: string; mode: "say"; requestId: number };
  onSubmit: (text: string) => void;
  onContinue: () => void;
  onRetry: () => void;
}

export type FantasyModeKey = Extract<ActionMode, "do" | "say"> | "cast" | "continue";
