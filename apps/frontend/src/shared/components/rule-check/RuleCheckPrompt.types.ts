import { RuleCheckOptionView } from "@/shared/types/check.types";

export interface RuleCheckPromptProps {
  prompt: string;
  options: RuleCheckOptionView[];
  remainingMs: number;
  windowMs: number;
  isSubmitting: boolean;
  isUntimed?: boolean;
  isRecall?: boolean;
  isDocked?: boolean;
  isLocked?: boolean;
  onChoose: (optionId: string) => void;
}
