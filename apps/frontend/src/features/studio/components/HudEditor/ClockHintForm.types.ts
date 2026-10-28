import type { SchemaFieldRef } from "../../lib/stateSchemaFields";
import type { ClockHint } from "@/shared/types/display-hints.types";

export interface ClockHintFormProps {
  current: { path: string; hint: ClockHint } | undefined;
  numberFields: SchemaFieldRef[];
  meterFields: { path: string; label: string }[];
  isSaving: boolean;
  onSave: (path: string, hint: ClockHint) => void;
  onRemove: (path: string) => void;
}
