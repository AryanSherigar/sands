import { COMPARISONS_BY_KIND } from "../constants/comparisons";
import type { HardLimitExample } from "../constants/hardLimits";
import type { InvariantCreate } from "../types/invariant.types";
import type { SentenceRow, ValueOption } from "../types/sentence.types";
import { buildNewLimit } from "./limitDraft";
import { buildSentenceMetadata, compileSentence, compileWhileLimit } from "./sentenceCompiler";

type ExampleRow = HardLimitExample["first"];

const findOption = (options: readonly ValueOption[], label: string): ValueOption | undefined =>
  options.find((option) => option.label.toLowerCase() === label.toLowerCase());

const resolveRow = (row: ExampleRow, options: readonly ValueOption[]): SentenceRow | null => {
  const option = findOption(options, row.valueLabel);
  if (!option || !COMPARISONS_BY_KIND[option.kind].includes(row.comparison)) return null;
  if (row.refLabel === undefined) return { path: option.path, comparison: row.comparison, amount: row.amount };
  const reference = findOption(options, row.refLabel);
  return reference ? { path: option.path, comparison: row.comparison, ref: reference.path } : null;
};

const resolveExpression = (
  example: HardLimitExample,
  options: readonly ValueOption[],
): Pick<InvariantCreate, "invariant_expression" | "metadata"> | null => {
  const first = resolveRow(example.first, options);
  const second = example.second ? resolveRow(example.second, options) : null;
  if (!first || (example.second && !second)) return null;
  const sentence = { rows: second ? [first, second] : [first], joiner: "and" as const };
  const expression = second ? compileWhileLimit(first, second) : compileSentence(sentence);
  return {
    invariant_expression: expression as unknown as Record<string, unknown>,
    metadata: buildSentenceMetadata(sentence) as unknown as Record<string, unknown>,
  };
};

export const buildLimitFromExample = (
  example: HardLimitExample,
  options: readonly ValueOption[],
): InvariantCreate => ({
  ...buildNewLimit(),
  label: example.label,
  narrator_text: example.text,
  ...(resolveExpression(example, options) ?? {}),
});
