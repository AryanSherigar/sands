import type { AttributeFieldSchema } from "../types/entity.types";
import type { StateFieldDefinition } from "../types/scenario.types";
import { buildValueKey } from "./trackedValueSchema";

export type CardValueKind = "number" | "boolean";

const DEFAULT_NUMBER_START = 0;

export const isEditableCardValue = (attribute: AttributeFieldSchema): boolean =>
  attribute.type === "number" || attribute.type === "boolean";

export const toValueField = (attribute: AttributeFieldSchema): StateFieldDefinition => ({
  type: attribute.type,
  ...(attribute.label === undefined ? {} : { label: attribute.label }),
  ...(attribute.initial === undefined ? {} : { initial: attribute.initial }),
  ...(attribute.min === undefined ? {} : { min: attribute.min }),
  ...(attribute.max === undefined ? {} : { max: attribute.max }),
});

export const toAttribute = (
  field: StateFieldDefinition,
  previous: AttributeFieldSchema,
): AttributeFieldSchema => ({
  type: field.type === "boolean" ? "boolean" : "number",
  is_narrator_visible: previous.is_narrator_visible ?? false,
  ...(field.label === undefined ? {} : { label: field.label }),
  ...(field.initial === undefined ? {} : { initial: field.initial }),
  ...(field.type === "number" && field.min !== undefined ? { min: field.min } : {}),
  ...(field.type === "number" && field.max !== undefined ? { max: field.max } : {}),
});

export const buildNewCardValue = (name: string, kind: CardValueKind): AttributeFieldSchema => ({
  type: kind,
  label: name.trim(),
  initial: kind === "boolean" ? false : DEFAULT_NUMBER_START,
  is_narrator_visible: false,
});

export const buildCardValueKey = (
  name: string,
  attributes: Record<string, AttributeFieldSchema>,
): string => buildValueKey(name, new Set(Object.keys(attributes)));

export const buildCardValuePath = (entityId: string, key: string): string => `${entityId}.${key}`;
