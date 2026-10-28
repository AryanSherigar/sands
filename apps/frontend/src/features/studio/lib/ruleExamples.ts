import { COMPARISONS_BY_KIND } from "../constants/comparisons";
import type { ConditionCreate } from "../types/condition.types";
import type { SentenceRow, ValueOption } from "../types/sentence.types";
import type { RuleExample } from "../constants/rules";
import { buildNewRule } from "./ruleDraft";
import { buildSentenceMetadata, compileSentence } from "./sentenceCompiler";

const findOption = (options: readonly ValueOption[], label: string): ValueOption | undefined =>
  options.find((option) => option.label.toLowerCase() === label.toLowerCase());

const resolveWhen = (example: RuleExample, options: readonly ValueOption[]): Partial<ConditionCreate> => {
  const option = findOption(options, example.when.valueLabel);
  if (!option || !COMPARISONS_BY_KIND[option.kind].includes(example.when.comparison)) return {};
  const row: SentenceRow = { path: option.path, comparison: example.when.comparison, amount: example.when.amount };
  const sentence = { rows: [row], joiner: "and" as const };
  return {
    condition_expression: compileSentence(sentence) as unknown as Record<string, unknown>,
    metadata: buildSentenceMetadata(sentence) as unknown as Record<string, unknown>,
  };
};

const resolveChange = (example: RuleExample, options: readonly ValueOption[]): Partial<ConditionCreate> => {
  const option = example.change ? findOption(options, example.change.valueLabel) : undefined;
  if (!example.change || !option) return {};
  return { state_mutations: [{ path: option.path, op: example.change.op, value: example.change.amount }] };
};

export const buildRuleFromExample = (
  example: RuleExample,
  options: readonly ValueOption[],
): ConditionCreate => ({
  ...buildNewRule(),
  label: example.title,
  narrator_instruction: example.instruction ?? "",
  is_one_shot: example.isOneShot,
  ...resolveWhen(example, options),
  ...resolveChange(example, options),
});
