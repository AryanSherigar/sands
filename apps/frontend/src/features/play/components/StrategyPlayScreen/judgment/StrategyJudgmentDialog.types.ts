import type { CourtLine } from "../../../lib/judgment-lines";
import type {
  JudgmentCourtMember,
  JudgmentNuanceId,
  JudgmentPronouncement,
  JudgmentVerdictId,
  StrategyJudgmentPackage,
} from "../../../types/judgmentScene.types";

export interface StrategyJudgmentDialogProps {
  isOpen: boolean;
  pkg: StrategyJudgmentPackage;
  liveText: string;
  isStreaming: boolean;
  failureMessage: string | null;
  canRetryOpen?: boolean;
  onRetryOpen?: () => void;
  onSpeak: (text: string) => Promise<boolean>;
  onPronounce: (pronouncement: JudgmentPronouncement) => Promise<boolean>;
  onDismissReveal: () => void;
  onClose: () => void;
}

export interface JudgmentTribunalStripProps {
  turn: number;
  summary: string;
}

export interface JudgmentAccusationPlaqueProps {
  charge: string;
  subjectLabel: string;
}

export interface JudgmentCourtCardProps {
  member: JudgmentCourtMember;
  isAccused: boolean;
}

export interface JudgmentManuscriptProps {
  pkg: StrategyJudgmentPackage;
  liveText: string;
  isStreaming: boolean;
}

export interface JudgmentVerdictPanelProps {
  selectedVerdict: JudgmentVerdictId;
  selectedNuance: JudgmentNuanceId | null;
  isDisabled: boolean;
  onSelectVerdict: (verdict: JudgmentVerdictId) => void;
  onSelectNuance: (nuance: JudgmentNuanceId) => void;
  onPronounce: () => void;
}

export interface JudgmentNuanceChipsProps {
  verdict: JudgmentVerdictId;
  selectedNuance: JudgmentNuanceId | null;
  onSelectNuance: (nuance: JudgmentNuanceId) => void;
}

export interface JudgmentActionBarProps {
  draftText: string;
  isBusy: boolean;
  canSpeak: boolean;
  onDraftChange: (text: string) => void;
  onSpeak: () => void;
  onWhisper: (text: string) => void;
}

export interface JudgmentExitConfirmProps {
  onStay: () => void;
  onLeave: () => void;
}

export interface JudgmentOutcomeRevealProps {
  lines: string[];
  onContinue: () => void;
}

export interface JudgmentCourtLinesProps {
  lines: CourtLine[];
}
