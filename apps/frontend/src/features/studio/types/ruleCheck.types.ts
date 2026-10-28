import type { RuleCheckKind } from "@/shared/types/check.types";
import type { StateMutation } from "@/shared/types/stateMutation.types";

export interface CheckOptionShape {
  id: string;
  label: string;
  result: string;
  mutations: StateMutation[];
  reopens: boolean;
}

export interface TimedChoiceParams {
  prompt: string;
  options: CheckOptionShape[];
  window_ms: number;
  timeout_result: string;
  hidden_result?: string | null;
  max_reopens?: number;
}

export interface RecallParams {
  prompt: string;
  variants: string[];
  correct_index: number;
  window_ms?: number;
  result_correct: string;
  result_wrong: string;
  result_timeout: string;
}

interface TimeEntryParams {
  prompt?: string;
  window_ms?: number;
}

type RuleCheckParams = TimedChoiceParams | RecallParams | TimeEntryParams;

export interface RuleCheckCreate {
  label: string;
  kind: RuleCheckKind;
  trigger_condition_expression?: Record<string, unknown>;
  priority?: number;
  result_path: string;
  params: RuleCheckParams;
  narrator_instruction_template?: string | null;
}

export type RuleCheckUpdate = Partial<RuleCheckCreate>;

export interface RuleCheckResponse {
  check_id: string;
  scenario_id: string;
  label: string;
  kind: RuleCheckKind;
  trigger_condition_expression: Record<string, unknown>;
  priority: number;
  result_path: string;
  params: RuleCheckParams;
  narrator_instruction_template: string | null;
}

export interface RuleCheckListResponse {
  items: RuleCheckResponse[];
}
