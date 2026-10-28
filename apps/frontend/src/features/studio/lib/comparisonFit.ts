import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COMPARISONS_BY_KIND } from "../constants/comparisons";
import type { SentenceMetadata, SentenceRow, ValueOption } from "../types/sentence.types";
import { readExpression } from "./endingDraft";
import { readSentenceMetadata } from "./sentenceMetadata";
import { parseExpression, parseWhileLimit } from "./sentenceCompiler";
import type { ValueUsages } from "./valueOptions";

const readRows = (expression: FieldExpression, metadata: SentenceMetadata | undefined): SentenceRow[] => {
  const limit = parseWhileLimit(expression, metadata);
  if (limit) return [limit.guard, limit.must];
  return parseExpression(expression, metadata)?.rows ?? [];
};

export const findMisfitLabels = (
  expression: FieldExpression | null,
  metadata: SentenceMetadata | undefined,
  options: readonly ValueOption[],
): string[] => {
  if (!expression) return [];
  const labels = readRows(expression, metadata).flatMap((row) => {
    const option = options.find((candidate) => candidate.path === row.path);
    const isFit = !option || COMPARISONS_BY_KIND[option.kind].includes(row.comparison);
    return isFit ? [] : [option.label];
  });
  return [...new Set(labels)];
};

export const countMisfitPlaces = (
  option: ValueOption,
  usages: Pick<ValueUsages, "endings" | "rules" | "limits">,
): number => {
  const places = [
    ...usages.endings.map((row) => [row.condition_expression, row.metadata] as const),
    ...usages.rules.map((row) => [row.condition_expression, row.metadata] as const),
    ...usages.limits.map((row) => [row.invariant_expression, row.metadata] as const),
  ];
  return places.filter(
    ([expression, metadata]) =>
      findMisfitLabels(readExpression(expression), readSentenceMetadata(metadata), [option]).length > 0,
  ).length;
};
