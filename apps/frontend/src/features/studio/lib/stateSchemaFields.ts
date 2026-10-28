import type {
  StateFieldDefinition,
  StateFieldOption,
} from "../types/scenario.types";

export interface SchemaFieldRef {
  path: string;
  label: string;
  definition: StateFieldDefinition;
}

export const enumOptionValues = (
  options: StateFieldOption[] | undefined,
): string[] =>
  (options ?? []).map((option) =>
    typeof option === "string" ? option : option.value,
  );

const listSchemaFields = (
  schema: Record<string, StateFieldDefinition>,
  prefix = "",
): SchemaFieldRef[] =>
  Object.entries(schema).flatMap(([key, definition]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (definition.type === "object") {
      return listSchemaFields(definition.fields ?? {}, path);
    }
    return [{ path, label: definition.label ?? path, definition }];
  });

export const listEnumFields = (
  schema: Record<string, StateFieldDefinition>,
): SchemaFieldRef[] =>
  listSchemaFields(schema).filter((field) => field.definition.type === "enum");

export const listNumberFields = (
  schema: Record<string, StateFieldDefinition>,
): SchemaFieldRef[] =>
  listSchemaFields(schema).filter((field) => field.definition.type === "number");
