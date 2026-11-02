import type {
  LetterSealHandler,
  LetterStage,
  ScribeDraftRequester,
  StrategyLetterPackage,
} from "../../../types/letterScene.types";

export interface StrategyLetterDialogProps {
  isOpen: boolean;
  pkg: StrategyLetterPackage;
  onSeal?: LetterSealHandler;
  onClose?: () => void;
  onRequestScribeDraft?: ScribeDraftRequester;
  onDecline?: () => void;
}

export interface LetterAmbientCanopyProps {
  stage: LetterStage;
  dispatchNumber: number;
  dateSolar: string;
  isMuted: boolean;
  onReturnToDesk: () => void;
  onToggleMute: () => void;
}
