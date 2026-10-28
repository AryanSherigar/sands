import type { ReactNode } from "react";
import type { SchemaFieldRef } from "../../lib/stateSchemaFields";

export interface FieldPickerSectionProps {
  title: string;
  fieldLabel: string;
  fields: SchemaFieldRef[];
  path: string;
  isPathLocked: boolean;
  problems: string[];
  isSaving: boolean;
  onPathChange: (path: string) => void;
  onSave: () => void;
  onRemove?: () => void;
  children: ReactNode;
}
