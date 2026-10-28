import { StateFieldDefinition } from "../../types/scenario.types";

export interface StateFieldRowProps {
  fieldKey: string;
  schema: StateFieldDefinition;
  enabledTools?: readonly string[];
  onRename: (oldKey: string, newKey: string) => void;
  onFieldChange: (key: string, patch: Partial<StateFieldDefinition>) => void;
  onRemove: (key: string) => void;
}
