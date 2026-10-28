import type { SchemaFieldRef } from "../../lib/stateSchemaFields";
import type { TierHint } from "@/shared/types/display-hints.types";

export interface TierHintFormProps {
  current: { path: string; hint: TierHint } | undefined;
  enumFields: SchemaFieldRef[];
  isSaving: boolean;
  onSave: (path: string, hint: TierHint) => void;
  onRemove: (path: string) => void;
}
