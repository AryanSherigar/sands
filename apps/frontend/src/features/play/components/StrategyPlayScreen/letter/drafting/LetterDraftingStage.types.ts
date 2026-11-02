import type {
  DraftRevision,
  IncomingLetterContent,
  LetterProvenance,
  ScribeProfile,
  StrategyLetterPackage,
} from "../../../../types/letterScene.types";

export interface LetterArchivalReferenceProps {
  incoming: IncomingLetterContent;
  provenance: LetterProvenance;
}

export interface LetterScribeInstructionBarProps {
  scribe: ScribeProfile;
  instruction: string;
  revisionIndex: number;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
}

export interface LetterParchmentCanvasProps {
  draft: DraftRevision;
  isDirectQuill: boolean;
  onUpdateBody: (text: string) => void;
}

export interface LetterDraftingActionsDeckProps {
  isSealing: boolean;
  onRewrite: (instruction: string) => void;
  onDiscard: () => void;
  onSealAndSend: () => void;
}

export interface LetterDraftingStageProps {
  pkg: StrategyLetterPackage;
  activeDraft: DraftRevision;
  mode: "direct_quill" | "scribe";
  canUndo: boolean;
  canRedo: boolean;
  isSealing: boolean;
  onRewrite: (instruction: string) => void;
  onUpdateBody: (text: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  onDiscard: () => void;
  onSealAndSend: () => void;
}
