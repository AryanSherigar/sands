import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import {
  AUTHORED_EFFECT_METADATA_KEYS,
  CUSTOM_TITLE_METADATA_KEY,
  DEFAULT_SOUND_SILENCE_MS,
  NEW_RULE_LABEL,
  RULE_LABEL_MAX_LENGTH,
} from "../constants/rules";
import { COPY_SUFFIX } from "../constants/advancedCards";
import type { StateMutation } from "@/shared/types/stateMutation.types";
import type { ConditionCreate, ConditionResponse, ConditionUpdate } from "../types/condition.types";
import type { SentenceMetadata, ValueOption } from "../types/sentence.types";
import { fromMutations, isChangeComplete, toMutations, type ChangeRow } from "./changeRows";
import { readExpression } from "./endingDraft";
import { describeSentence, parseExpression } from "./sentenceCompiler";
import { readSentenceMetadata, toStoredMetadata } from "./sentenceMetadata";
import { extractFieldPaths } from "./valueOptions";

export interface SoundDraft {
  cue: string;
  cutAmbient: boolean;
  silenceMs: number;
}

export interface RuleDraft {
  title: string;
  hasAuthoredEffects: boolean;
  expression: FieldExpression | null;
  metadata: SentenceMetadata | undefined;
  isOneShot: boolean;
  instruction: string;
  changes: ChangeRow[];
  sound: SoundDraft;
}

export const buildLabelMap = (options: readonly ValueOption[]): Record<string, string> =>
  Object.fromEntries(options.map((option) => [option.path, option.label]));

export const buildAutoTitle = (
  expression: FieldExpression | null,
  metadata: SentenceMetadata | undefined,
  labels: Record<string, string>,
): string | null => {
  const sentence = expression ? parseExpression(expression, metadata) : null;
  if (!sentence) return null;
  return `When ${describeSentence(sentence, labels)}`.slice(0, RULE_LABEL_MAX_LENGTH);
};

const readStoredMutations = (row: ConditionResponse): StateMutation[] => {
  if (row.state_mutations.length > 0) return row.state_mutations;
  return row.state_mutation ? [row.state_mutation] : [];
};

export const buildRuleDraft = (row: ConditionResponse, options: readonly ValueOption[]): RuleDraft => {
  const expression = readExpression(row.condition_expression);
  const metadata = readSentenceMetadata(row.metadata);
  const autoTitle = buildAutoTitle(expression, metadata, buildLabelMap(options));
  const isCustom = row.metadata?.[CUSTOM_TITLE_METADATA_KEY] === true;
  const isAutoLabel = !isCustom && (row.label === autoTitle || row.label === NEW_RULE_LABEL);
  return {
    title: isAutoLabel ? "" : row.label,
    hasAuthoredEffects: AUTHORED_EFFECT_METADATA_KEYS.some((key) => row.metadata?.[key] !== undefined),
    expression,
    metadata,
    isOneShot: row.is_one_shot,
    instruction: row.narrator_instruction,
    changes: fromMutations(readStoredMutations(row), options),
    sound: {
      cue: row.sensory_cue ?? "",
      cutAmbient: row.cut_ambient,
      silenceMs: row.silence_duration_ms,
    },
  };
};

export const isThenEmpty = (draft: RuleDraft): boolean =>
  draft.instruction.trim() === "" &&
  !draft.changes.some(isChangeComplete) &&
  draft.sound.cue === "" &&
  !draft.hasAuthoredEffects;

const buildLabel = (draft: RuleDraft, options: readonly ValueOption[]): string =>
  draft.title.trim() ||
  buildAutoTitle(draft.expression, draft.metadata, buildLabelMap(options)) ||
  NEW_RULE_LABEL;

const isSameExpression = (row: ConditionResponse, draft: RuleDraft): boolean =>
  JSON.stringify(row.condition_expression ?? {}) === JSON.stringify(draft.expression ?? {});

const addSoundPatch = (patch: ConditionUpdate, row: ConditionResponse, draft: RuleDraft): void => {
  if (draft.sound.cue !== (row.sensory_cue ?? "")) patch.sensory_cue = draft.sound.cue || null;
  if (draft.sound.cutAmbient !== row.cut_ambient) patch.cut_ambient = draft.sound.cutAmbient;
  if (draft.sound.silenceMs !== row.silence_duration_ms) patch.silence_duration_ms = draft.sound.silenceMs;
};

const addChangesPatch = (patch: ConditionUpdate, row: ConditionResponse, draft: RuleDraft): void => {
  const next = toMutations(draft.changes);
  if (JSON.stringify(next) === JSON.stringify(readStoredMutations(row))) return;
  patch.state_mutations = next;
  if (row.state_mutation) patch.state_mutation = null;
};

export interface RuleBlocks {
  isExpressionBlocked: boolean;
  isChangesBlocked: boolean;
}

const readCustomTitleFlag = (row: ConditionResponse): boolean => row.metadata?.[CUSTOM_TITLE_METADATA_KEY] === true;

const addExpressionPatch = (patch: ConditionUpdate, row: ConditionResponse, draft: RuleDraft): void => {
  const hasCustomTitle = draft.title.trim() !== "";
  const isExpressionChanged = !isSameExpression(row, draft);
  if (!isExpressionChanged && hasCustomTitle === readCustomTitleFlag(row)) return;
  const stored = toStoredMetadata(isExpressionChanged ? draft.metadata : readSentenceMetadata(row.metadata), row.metadata) ?? {};
  const { [CUSTOM_TITLE_METADATA_KEY]: _flag, ...rest } = stored;
  patch.metadata = hasCustomTitle ? { ...rest, [CUSTOM_TITLE_METADATA_KEY]: true } : rest;
  if (isExpressionChanged) patch.condition_expression = (draft.expression ?? {}) as unknown as Record<string, unknown>;
};

export const buildRulePatch = (
  row: ConditionResponse,
  draft: RuleDraft,
  options: readonly ValueOption[],
  blocks: RuleBlocks = { isExpressionBlocked: false, isChangesBlocked: false },
): ConditionUpdate => {
  const patch: ConditionUpdate = {};
  const isLabelBlocked = blocks.isExpressionBlocked && draft.title.trim() === "";
  const label = buildLabel(draft, options);
  if (!isLabelBlocked && label !== row.label) patch.label = label;
  if (draft.instruction !== row.narrator_instruction) patch.narrator_instruction = draft.instruction;
  if (draft.isOneShot !== row.is_one_shot) patch.is_one_shot = draft.isOneShot;
  if (!blocks.isExpressionBlocked) addExpressionPatch(patch, row, draft);
  if (!blocks.isChangesBlocked) addChangesPatch(patch, row, draft);
  addSoundPatch(patch, row, draft);
  return patch;
};

export const buildNewRule = (): ConditionCreate => ({
  label: NEW_RULE_LABEL,
  narrator_instruction: "",
  condition_expression: {},
  state_mutations: [],
  is_one_shot: false,
});

export const buildRuleCopy = (row: ConditionResponse): ConditionCreate => ({
  label: `${row.label} (${COPY_SUFFIX})`.slice(0, RULE_LABEL_MAX_LENGTH),
  narrator_instruction: row.narrator_instruction,
  condition_expression: row.condition_expression,
  metadata: row.metadata,
  state_mutations: readStoredMutations(row),
  is_one_shot: row.is_one_shot,
  ...(row.sensory_cue
    ? {
        sensory_cue: row.sensory_cue,
        cut_ambient: row.cut_ambient,
        silence_duration_ms: row.silence_duration_ms || DEFAULT_SOUND_SILENCE_MS,
      }
    : {}),
});

const readRepeatBound = (op: ChangeRow["op"], option: ValueOption | undefined): number | undefined => {
  if (op === "decrement") return option?.min;
  return op === "increment" ? option?.max : undefined;
};

export const findSelfRepeatMessage = (
  draft: RuleDraft,
  options: readonly ValueOption[],
): string | null => {
  if (draft.isOneShot || !draft.expression) return null;
  const checked = extractFieldPaths(draft.expression as unknown as Record<string, unknown>);
  const repeating = draft.changes.find((change) => isChangeComplete(change) && checked.has(change.path));
  if (!repeating) return null;
  const option = options.find((candidate) => candidate.path === repeating.path);
  const name = option?.label ?? repeating.path;
  const bound = readRepeatBound(repeating.op, option);
  if (bound === undefined) {
    return `This will repeat every turn while ${name} still matches the condition. Is that what you want?`;
  }
  return `This will repeat every turn until ${name} is ${bound}. Is that what you want?`;
};
