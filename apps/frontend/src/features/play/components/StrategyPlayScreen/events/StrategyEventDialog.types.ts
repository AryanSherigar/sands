import type { StrategyEventPackage } from "../../../types/eventScene.types";

export type { StrategyEventPackage };

export interface StrategyEventDialogProps {
  isOpen: boolean;
  eventPackage: StrategyEventPackage | null;
  onSelectOption: (optionId: string) => void;
  onCancelQueued?: (commandId: string) => void;
  onClose?: () => void;
}
