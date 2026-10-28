import type { ChecklistItem, RequiredItemId, SuggestionId } from "../../lib/finishChecklist";
import type { ReactNode } from "react";
import type { SetupInputField } from "@/shared/types/scenario.types";
import type { GuideStepDefinition } from "../../constants/guideSteps";
import type { PickOption } from "../../types/guide.types";
import type { LoreDocument } from "../../types/lore.types";

export interface OtherTypePromptProps {
  isOpen: boolean;
  onSubmit: (typeName: string) => void;
  onClose: () => void;
}

export interface GuideScenarioProviderProps {
  scenarioId: string | null;
  onDraftCreated: (scenarioId: string) => void;
  children: ReactNode;
}

export interface GuideStepLayoutProps {
  step: GuideStepDefinition;
  children: ReactNode;
  shouldShowExample?: boolean;
}

export interface ShowExampleProps {
  stepId: GuideStepDefinition["id"];
}

export interface StepBarProps {
  step: GuideStepDefinition;
  stepCount: number;
  onBack: () => void;
  onSkipToEditor: () => void;
}

export interface GuideTextFieldProps {
  label: string;
  helper: string;
  value: string;
  maxLength: number;
  placeholder?: string;
  isLarge?: boolean;
  onChange: (next: string) => void;
}

export interface GuideChipProps {
  label: string;
  isSelected?: boolean;
  badge?: string;
  onClick: () => void;
}

export interface SetupFieldRowProps {
  field: SetupInputField;
  onChange: (updates: Partial<SetupInputField>) => void;
  onRemove: () => void;
}

export interface SetupPreviewProps {
  fields: SetupInputField[];
}

export interface PlayerNameChipPreviewProps {
  document: LoreDocument;
}

export interface StartsAtPickerProps {
  document: LoreDocument;
  places: PickOption[];
  onChange: (next: LoreDocument) => void;
}

export interface PlayOpeningButtonProps {
  document: LoreDocument;
}

export interface StyleChipsProps {
  document: LoreDocument;
  onChange: (next: LoreDocument) => void;
}

export interface AdvancedInvitationProps {
  canUseAdvanced: boolean;
  isPublishing: boolean;
  isBusy: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

export interface FinishPreviewCardProps {
  title: string;
  logline: string | null;
  coverImageUrl: string | null;
  primaryGenre: string | null;
}

export interface FinishChecklistProps {
  requiredItems: ChecklistItem<RequiredItemId>[];
  suggestions: ChecklistItem<SuggestionId>[];
  onFix: (stepNumber: number) => void;
}

export interface FinishActionsProps {
  isPublishDisabled: boolean;
  isBusy: boolean;
  isLive: boolean;
  missingMessage: string | null;
  failureMessage: string | null;
  onPlaytest: () => void;
  onPublish: () => void;
}
