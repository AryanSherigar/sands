import type { ConditionResponse } from "../types/condition.types";
import type { EndConditionResponse } from "../types/end_condition.types";
import type { AttributeFieldSchema, EntityResponse } from "../types/entity.types";
import type { FactResponse } from "../types/fact.types";
import type { InvariantResponse } from "../types/invariant.types";
import type { StateFieldDefinition, StateFieldType } from "../types/scenario.types";
import type { ValueKind, ValueOption } from "../types/sentence.types";
import { enumOptionValues } from "./stateSchemaFields";
import { RESERVED_VALUE_KEYS } from "./trackedValueSchema";

type ExpressionNode = Record<string, unknown> | null | undefined;

export interface ValueUsages {
  endings: EndConditionResponse[];
  rules: ConditionResponse[];
  limits: InvariantResponse[];
}

const CONNECTIVE_KEYS = ["AND", "OR", "NOT"] as const;
const WORD_SEPARATOR = /[_\s]+/;

const STATE_KINDS: Partial<Record<StateFieldType, ValueKind>> = {
  number: "number",
  boolean: "boolean",
  enum: "enum",
};

const ATTRIBUTE_KINDS: Partial<Record<AttributeFieldSchema["type"], ValueKind>> = {
  number: "number",
  boolean: "boolean",
  enum: "enum",
};

export const humanizeKey = (key: string): string => {
  const words = key.split(WORD_SEPARATOR).filter(Boolean).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
};

const toTrackedOption = (path: string, field: StateFieldDefinition, kind: ValueKind): ValueOption => ({
  path,
  label: field.label?.trim() || humanizeKey(path.split(".").at(-1) ?? path),
  kind,
  source: "tracked",
  ...(kind === "enum" ? { options: enumOptionValues(field.options) } : {}),
  ...(field.min === undefined ? {} : { min: field.min }),
  ...(field.max === undefined ? {} : { max: field.max }),
});

export const listTrackedValueOptions = (
  schema: Record<string, StateFieldDefinition>,
  prefix = "",
): ValueOption[] =>
  Object.entries(schema).flatMap(([key, field]) => {
    const path = `${prefix}${key}`;
    if (field.type === "object") return listTrackedValueOptions(field.fields ?? {}, `${path}.`);
    const kind = STATE_KINDS[field.type];
    return kind ? [toTrackedOption(path, field, kind)] : [];
  });

const toCardOption = (
  entity: EntityResponse,
  key: string,
  field: AttributeFieldSchema,
  kind: ValueKind,
): ValueOption => ({
  path: `${entity.entity_id}.${key}`,
  label: `${entity.canonical_name}'s ${field.label?.trim() || humanizeKey(key)}`,
  kind,
  source: "card",
  ...(kind === "enum" ? { options: [] } : {}),
  ...(field.min === undefined ? {} : { min: field.min }),
  ...(field.max === undefined ? {} : { max: field.max }),
});

const listCardValueOptions = (entities: readonly EntityResponse[]): ValueOption[] =>
  entities.flatMap((entity) =>
    Object.entries(entity.attributes_schema ?? {}).flatMap(([key, field]) => {
      const kind = ATTRIBUTE_KINDS[field.type];
      return kind ? [toCardOption(entity, key, field, kind)] : [];
    }),
  );

export const buildValueOptions = (
  schema: Record<string, StateFieldDefinition>,
  entities: readonly EntityResponse[],
): ValueOption[] => [...listTrackedValueOptions(schema), ...listCardValueOptions(entities)];

const PATH_SEPARATOR = ".";

const listStatePaths = (schema: Record<string, StateFieldDefinition>, prefix = ""): string[] =>
  Object.entries(schema).flatMap(([key, field]) => {
    const path = `${prefix}${key}`;
    return field.type === "object" ? [path, ...listStatePaths(field.fields ?? {}, `${path}${PATH_SEPARATOR}`)] : [path];
  });

const listCardPaths = (entities: readonly EntityResponse[]): string[] =>
  entities.flatMap((entity) =>
    Object.keys(entity.attributes_schema ?? {}).map((key) => `${entity.entity_id}${PATH_SEPARATOR}${key}`),
  );

export const buildUnsupportedPathCheck = (
  schema: Record<string, StateFieldDefinition>,
  entities: readonly EntityResponse[],
  options: readonly ValueOption[],
): ((path: string) => boolean) => {
  const known = new Set([...listStatePaths(schema), ...listCardPaths(entities)]);
  const supported = new Set(options.map((option) => option.path));
  return (path) => {
    if (path === "" || supported.has(path)) return false;
    const root = path.split(PATH_SEPARATOR)[0];
    return known.has(path) || RESERVED_VALUE_KEYS.has(root);
  };
};

export const extractFieldPaths = (expression: ExpressionNode): Set<string> => {
  const paths = new Set<string>();
  if (!expression) return paths;
  if (typeof expression.field === "string") paths.add(expression.field);
  if (typeof expression.ref === "string") paths.add(expression.ref);
  CONNECTIVE_KEYS.forEach((key) => {
    const nested = expression[key];
    if (typeof nested === "object" && nested !== null) {
      extractFieldPaths(nested as ExpressionNode).forEach((path) => paths.add(path));
    }
  });
  return paths;
};

const conditionPaths = (condition: ConditionResponse): Set<string> => {
  const paths = extractFieldPaths(condition.condition_expression);
  condition.state_mutations.forEach((mutation) => paths.add(mutation.path));
  if (condition.state_mutation) paths.add(condition.state_mutation.path);
  return paths;
};

export const findValueUsages = (
  path: string,
  rows: {
    endConditions: readonly EndConditionResponse[];
    conditions: readonly ConditionResponse[];
    invariants: readonly InvariantResponse[];
  },
): ValueUsages => ({
  endings: rows.endConditions.filter((row) => extractFieldPaths(row.condition_expression).has(path)),
  rules: rows.conditions.filter((row) => conditionPaths(row).has(path)),
  limits: rows.invariants.filter((row) => extractFieldPaths(row.invariant_expression).has(path)),
});

export const findLinkUsages = (path: string, facts: readonly FactResponse[]): FactResponse[] =>
  facts.filter((fact) => extractFieldPaths(fact.when_active).has(path));

export const countValueUsages = (usages: ValueUsages): number =>
  usages.endings.length + usages.rules.length + usages.limits.length;
