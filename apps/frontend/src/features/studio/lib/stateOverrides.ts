import type { Comparison, Sentence, SentenceRow, ValueOption } from "../types/sentence.types";

const AT_MOST_COMPARISONS: readonly Comparison[] = ["drops_to", "at_most"];
const AT_LEAST_COMPARISONS: readonly Comparison[] = ["rises_to", "at_least"];

const pickAtMost = (row: SentenceRow, option: ValueOption): number | undefined =>
  typeof row.amount === "number" ? row.amount : option.min;

const pickAtLeast = (row: SentenceRow, option: ValueOption): number | undefined =>
  typeof row.amount === "number" ? row.amount : option.max;

const pickValue = (row: SentenceRow, option: ValueOption): number | string | boolean | undefined => {
  if (row.comparison === "becomes_yes") return true;
  if (row.comparison === "becomes_no") return false;
  if (row.comparison === "becomes_option") return typeof row.amount === "string" ? row.amount : undefined;
  if (row.comparison === "exactly") return row.amount;
  if (AT_MOST_COMPARISONS.includes(row.comparison)) return pickAtMost(row, option);
  if (AT_LEAST_COMPARISONS.includes(row.comparison)) return pickAtLeast(row, option);
  return undefined;
};

const isPresettable = (row: SentenceRow, option: ValueOption | undefined): option is ValueOption =>
  option !== undefined && option.source === "tracked" && row.ref === undefined;

const findPresetValue = (
  row: SentenceRow,
  options: readonly ValueOption[],
): number | string | boolean | undefined => {
  const option = options.find((candidate) => candidate.path === row.path);
  return isPresettable(row, option) ? pickValue(row, option) : undefined;
};

const presetRow = (
  overrides: Record<string, unknown>,
  row: SentenceRow,
  options: readonly ValueOption[],
): void => {
  const value = findPresetValue(row, options);
  if (value !== undefined) overrides[row.path] = value;
};

export const overridesForSentence = (
  sentence: Sentence,
  options: readonly ValueOption[],
): Record<string, unknown> => {
  const overrides: Record<string, unknown> = {};
  if (sentence.joiner === "and") {
    sentence.rows.forEach((row) => presetRow(overrides, row, options));
    return overrides;
  }
  const firstPresettable = sentence.rows.find((row) => findPresetValue(row, options) !== undefined);
  if (firstPresettable) presetRow(overrides, firstPresettable, options);
  return overrides;
};

export const listCardValueLabels = (
  sentence: Sentence,
  options: readonly ValueOption[],
): string[] =>
  sentence.rows.flatMap((row) => {
    const option = options.find((candidate) => candidate.path === row.path);
    return option?.source === "card" ? [option.label] : [];
  });
