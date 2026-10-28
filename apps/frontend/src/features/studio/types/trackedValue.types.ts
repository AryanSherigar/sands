import type { ValueKind } from "./sentence.types";

export interface NewTrackedValue {
  name: string;
  kind: ValueKind;
  initial?: number | boolean | string;
  min?: number;
  max?: number;
  options?: string[];
  description?: string;
  display?: Record<string, unknown>;
}
