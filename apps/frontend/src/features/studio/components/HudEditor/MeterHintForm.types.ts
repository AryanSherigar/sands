import type { SchemaFieldRef } from "../../lib/stateSchemaFields";
import type { MeterHint } from "@/shared/types/display-hints.types";

export interface MeterHintFormProps {
  current: { path: string; hint: MeterHint } | undefined;
  numberFields: SchemaFieldRef[];
  isSaving: boolean;
  onSave: (path: string, hint: MeterHint) => void;
  onRemove: (path: string) => void;
}
