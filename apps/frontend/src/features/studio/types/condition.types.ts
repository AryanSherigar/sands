// StateMutation/StateMutationOp moved to shared/types/stateMutation.types.ts
// (single source of truth — play/'s minigame result handling needs this
// shape too, and features never import from each other). Re-exported here
// so existing imports from "../../types/condition.types" keep working.
import type { StateMutation } from "@/shared/types/stateMutation.types";
export type { StateMutation } from "@/shared/types/stateMutation.types";

export interface ConditionCreate {
  label: string;
  condition_expression?: Record<string, unknown>;
  narrator_instruction: string;
  metadata?: Record<string, unknown>;
  state_mutation?: StateMutation;
  state_mutations?: StateMutation[];
  is_one_shot?: boolean;
  sensory_cue?: string | null;
  cut_ambient?: boolean;
  silence_duration_ms?: number;
}

export type ConditionUpdate = Partial<Omit<ConditionCreate, "state_mutation">> & {
  state_mutation?: StateMutation | null;
};

export interface ConditionResponse {
  condition_id: string;
  scenario_id: string;
  label: string;
  condition_expression: Record<string, unknown>;
  condition_version: string;
  narrator_instruction: string;
  metadata: Record<string, unknown>;
  state_mutation: StateMutation | null;
  state_mutations: StateMutation[];
  is_one_shot: boolean;
  sensory_cue: string | null;
  cut_ambient: boolean;
  silence_duration_ms: number;
}

export interface ConditionListResponse {
  items: ConditionResponse[];
}
