export interface TimeEntryPromptProps {
  prompt: string;
  toldLabel: string | null;
  wallLabel: string | null;
  enterLabel: string;
  rejectLabel: string;
  remainingMs: number;
  windowMs: number;
  isSubmitting: boolean;
  isUntimed?: boolean;
  isDocked?: boolean;
  isLocked?: boolean;
  onEnter: (entryText: string) => void;
  onReject: () => void;
}
