import type { StateMutation, StateMutationOp } from "@/shared/types/stateMutation.types";
import type { ValueKind, ValueOption } from "../types/sentence.types";

export interface ChangeRow {
  id: string;
  path: string;
  op: StateMutationOp;
  value: number | boolean | string | undefined;
}

export const buildEmptyChangeRow = (id: string): ChangeRow => ({ id, path: "", op: "set", value: undefined });

export const listOpsForKind = (kind: ValueKind | undefined): StateMutationOp[] =>
  kind === "number" ? ["set", "increment", "decrement"] : ["set"];

const normalizeValue = (value: unknown, kind: ValueKind | undefined): ChangeRow["value"] => {
  if (kind === "number") return typeof value === "number" ? value : Number(value);
  if (kind === "boolean") return value === true || value === "true";
  return typeof value === "string" ? value : String(value ?? "");
};

export const fromMutations = (
  mutations: readonly StateMutation[],
  options: readonly ValueOption[],
): ChangeRow[] =>
  mutations.map((mutation, index) => {
    const kind = options.find((option) => option.path === mutation.path)?.kind;
    return { id: `change-${index}`, path: mutation.path, op: mutation.op, value: normalizeValue(mutation.value, kind) };
  });

export const isChangeComplete = (row: ChangeRow): boolean =>
  row.path !== "" && row.value !== undefined && !(typeof row.value === "number" && Number.isNaN(row.value));

export const toMutations = (rows: readonly ChangeRow[]): StateMutation[] =>
  rows.filter(isChangeComplete).map((row) => ({ path: row.path, op: row.op, value: row.value }));

const hasNoOption = (row: ChangeRow, options: readonly ValueOption[]): boolean =>
  row.path !== "" && !options.some((option) => option.path === row.path);

export const findMissingChangePaths = (
  rows: readonly ChangeRow[],
  options: readonly ValueOption[],
  isUnsupportedPath: (path: string) => boolean = () => false,
): string[] =>
  rows.filter((row) => hasNoOption(row, options) && !isUnsupportedPath(row.path)).map((row) => row.path);

export const findUnsupportedChangePaths = (
  rows: readonly ChangeRow[],
  isUnsupportedPath: (path: string) => boolean,
): string[] => rows.filter((row) => isUnsupportedPath(row.path)).map((row) => row.path);
