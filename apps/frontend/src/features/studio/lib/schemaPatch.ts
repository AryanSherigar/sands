import type { StateFieldDefinition } from "../types/scenario.types";

type Schema = Record<string, StateFieldDefinition>;

// Returns a copy of the schema with `patch` merged into the field at the dotted
// path. A patch value of undefined removes that key from the field.
export const patchFieldAtPath = (
  schema: Schema,
  path: string,
  patch: Partial<StateFieldDefinition>,
): Schema => {
  const [head, ...rest] = path.split(".");
  const field = schema[head];
  if (!field) return schema;
  if (rest.length === 0) {
    return { ...schema, [head]: applyPatch(field, patch) };
  }
  const nested = patchFieldAtPath(field.fields ?? {}, rest.join("."), patch);
  return { ...schema, [head]: { ...field, fields: nested } };
};

const applyPatch = (
  field: StateFieldDefinition,
  patch: Partial<StateFieldDefinition>,
): StateFieldDefinition => {
  const merged: Record<string, unknown> = { ...field, ...patch };
  for (const key of Object.keys(patch)) {
    if (merged[key] === undefined) delete merged[key];
  }
  return merged as unknown as StateFieldDefinition;
};
