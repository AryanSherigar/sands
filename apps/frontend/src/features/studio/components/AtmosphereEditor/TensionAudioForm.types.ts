import type { TierHint } from "@/shared/types/display-hints.types";

export interface TensionAudioFormProps {
  path: string;
  hint: TierHint;
  options: string[];
  isSaving: boolean;
  onSave: (path: string, hint: TierHint) => void;
}
