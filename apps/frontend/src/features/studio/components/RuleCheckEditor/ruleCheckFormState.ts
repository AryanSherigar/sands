import {
  DEFAULT_MAX_REOPENS,
  DEFAULT_RECALL_WINDOW_MS,
  DEFAULT_TIMED_WINDOW_MS,
  MAX_CHECK_OPTIONS,
  MAX_RECALL_VARIANTS,
  MAX_VARIANT_LENGTH,
  MAX_WINDOW_MS,
  MIN_CHECK_OPTIONS,
  MIN_RECALL_VARIANTS,
  MIN_WINDOW_MS,
  MS_PER_SECOND,
} from "../../constants/ruleCheck";
import type {
  CheckOptionShape,
  RecallParams,
  RuleCheckCreate,
  RuleCheckResponse,
  TimedChoiceParams,
} from "../../types/ruleCheck.types";
import type { FieldExpression } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import type { RuleCheckKind } from "@/shared/types/check.types";

const OPTION_ID_PATTERN = /^[a-z][a-z0-9_]{0,30}$/;

export interface TimedFormState {
  prompt: string;
  options: CheckOptionShape[];
  windowSeconds: number;
  timeoutResult: string;
  hiddenResult: string;
  maxReopens: number;
}

export interface RecallFormState {
  prompt: string;
  variants: string[];
  correctIndex: number;
  windowSeconds: number;
  resultCorrect: string;
  resultWrong: string;
  resultTimeout: string;
}

export interface RuleCheckFormState {
  label: string;
  kind: RuleCheckKind;
  trigger: FieldExpression | null;
  resultPath: string;
  narratorTemplate: string;
  timed: TimedFormState;
  recall: RecallFormState;
}

export const buildEmptyOption = (index: number): CheckOptionShape => ({
  id: `option_${index + 1}`,
  label: "",
  result: "",
  mutations: [],
  reopens: false,
});

const EMPTY_TIMED: TimedFormState = {
  prompt: "",
  options: [buildEmptyOption(0), buildEmptyOption(1)],
  windowSeconds: DEFAULT_TIMED_WINDOW_MS / MS_PER_SECOND,
  timeoutResult: "",
  hiddenResult: "",
  maxReopens: DEFAULT_MAX_REOPENS,
};

const EMPTY_RECALL: RecallFormState = {
  prompt: "",
  variants: ["", ""],
  correctIndex: 0,
  windowSeconds: DEFAULT_RECALL_WINDOW_MS / MS_PER_SECOND,
  resultCorrect: "",
  resultWrong: "",
  resultTimeout: "",
};

const timedFrom = (params: TimedChoiceParams): TimedFormState => ({
  prompt: params.prompt,
  options: params.options.map((option) => ({
    ...option,
    mutations: option.mutations ?? [],
  })),
  windowSeconds: params.window_ms / MS_PER_SECOND,
  timeoutResult: params.timeout_result,
  hiddenResult: params.hidden_result ?? "",
  maxReopens: params.max_reopens ?? DEFAULT_MAX_REOPENS,
});

const recallFrom = (params: RecallParams): RecallFormState => ({
  prompt: params.prompt,
  variants: [...params.variants],
  correctIndex: params.correct_index,
  windowSeconds: (params.window_ms ?? DEFAULT_RECALL_WINDOW_MS) / MS_PER_SECOND,
  resultCorrect: params.result_correct,
  resultWrong: params.result_wrong,
  resultTimeout: params.result_timeout,
});

export const buildInitialState = (
  check: RuleCheckResponse | null,
): RuleCheckFormState => ({
  label: check?.label ?? "",
  kind: check?.kind ?? "timed_choice",
  trigger:
    (check?.trigger_condition_expression as unknown as FieldExpression) ?? null,
  resultPath: check?.result_path ?? "",
  narratorTemplate: check?.narrator_instruction_template ?? "",
  timed:
    check?.kind === "timed_choice"
      ? timedFrom(check.params as TimedChoiceParams)
      : EMPTY_TIMED,
  recall:
    check?.kind === "recall"
      ? recallFrom(check.params as RecallParams)
      : EMPTY_RECALL,
});

const toWindowMs = (seconds: number): number =>
  Math.round(seconds * MS_PER_SECOND);

const timedParams = (state: TimedFormState): TimedChoiceParams => ({
  prompt: state.prompt,
  options: state.options,
  window_ms: toWindowMs(state.windowSeconds),
  timeout_result: state.timeoutResult,
  hidden_result: state.hiddenResult || null,
  max_reopens: state.maxReopens,
});

const recallParams = (state: RecallFormState): RecallParams => ({
  prompt: state.prompt,
  variants: state.variants,
  correct_index: state.correctIndex,
  window_ms: toWindowMs(state.windowSeconds),
  result_correct: state.resultCorrect,
  result_wrong: state.resultWrong,
  result_timeout: state.resultTimeout,
});

export const buildPayload = (state: RuleCheckFormState): RuleCheckCreate => ({
  label: state.label,
  kind: state.kind,
  trigger_condition_expression:
    (state.trigger as unknown as Record<string, unknown>) ?? {},
  result_path: state.resultPath,
  params:
    state.kind === "timed_choice"
      ? timedParams(state.timed)
      : recallParams(state.recall),
  narrator_instruction_template: state.narratorTemplate || null,
});

const windowProblems = (seconds: number): string[] => {
  const windowMs = toWindowMs(seconds);
  const isOutOfRange = windowMs < MIN_WINDOW_MS || windowMs > MAX_WINDOW_MS;
  return isOutOfRange ? ["The window must be between 1 and 120 seconds."] : [];
};

const optionProblems = (
  options: CheckOptionShape[],
  allowedResults: string[],
): string[] => {
  const problems: string[] = [];
  if (options.length < MIN_CHECK_OPTIONS || options.length > MAX_CHECK_OPTIONS) {
    problems.push(`Use between ${MIN_CHECK_OPTIONS} and ${MAX_CHECK_OPTIONS} options.`);
  }
  const ids = options.map((option) => option.id);
  if (new Set(ids).size !== ids.length) problems.push("Option ids must be unique.");
  if (ids.some((id) => !OPTION_ID_PATTERN.test(id))) {
    problems.push("Option ids use lowercase letters, digits and underscores.");
  }
  if (options.some((option) => !option.label.trim())) {
    problems.push("Every option needs a label.");
  }
  if (options.some((option) => !allowedResults.includes(option.result))) {
    problems.push("Every option needs a result from the chosen field.");
  }
  return problems;
};

const timedProblems = (
  state: TimedFormState,
  allowedResults: string[],
): string[] => {
  const problems = optionProblems(state.options, allowedResults);
  if (!state.prompt.trim()) problems.push("The prompt cannot be empty.");
  if (!allowedResults.includes(state.timeoutResult)) {
    problems.push("Choose the result for running out of time.");
  }
  if (state.hiddenResult && !allowedResults.includes(state.hiddenResult)) {
    problems.push("The hidden-tab result must be a result of the chosen field.");
  }
  return [...problems, ...windowProblems(state.windowSeconds)];
};

const variantProblems = (variants: string[]): string[] => {
  const problems: string[] = [];
  const isCountValid =
    variants.length >= MIN_RECALL_VARIANTS && variants.length <= MAX_RECALL_VARIANTS;
  if (!isCountValid) {
    problems.push(`Use between ${MIN_RECALL_VARIANTS} and ${MAX_RECALL_VARIANTS} wordings.`);
  }
  if (variants.some((text) => !text.trim() || text.length > MAX_VARIANT_LENGTH)) {
    problems.push(`Each wording needs 1 to ${MAX_VARIANT_LENGTH} characters.`);
  }
  if (new Set(variants).size !== variants.length) {
    problems.push("Wordings must be different from each other.");
  }
  return problems;
};

const recallProblems = (
  state: RecallFormState,
  allowedResults: string[],
): string[] => {
  const problems = variantProblems(state.variants);
  if (!state.prompt.trim()) problems.push("The prompt cannot be empty.");
  const results = [state.resultCorrect, state.resultWrong, state.resultTimeout];
  if (results.some((result) => !allowedResults.includes(result))) {
    problems.push("Choose a result for correct, wrong and timeout.");
  }
  return [...problems, ...windowProblems(state.windowSeconds)];
};

export const getFormProblems = (
  state: RuleCheckFormState,
  allowedResults: string[],
): string[] => {
  const problems: string[] = [];
  if (!state.label.trim()) problems.push("Give the check a name.");
  if (!state.resultPath) problems.push("Choose the tracked value that receives the answer.");
  const kindProblems =
    state.kind === "timed_choice"
      ? timedProblems(state.timed, allowedResults)
      : recallProblems(state.recall, allowedResults);
  return [...problems, ...kindProblems];
};
