import type { MeterHint } from "@/shared/types/display-hints.types";

export interface ReaderEffectsFormProps {
  path: string;
  hint: MeterHint;
  isSaving: boolean;
  onSave: (path: string, hint: MeterHint) => void;
}
