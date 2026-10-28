import type { RuleHand } from "@/shared/types/rule-sheet.types";
import type { InitialRuleStatus } from "../constants/sheetRule";

export interface SheetRuleCreate {
  key: string;
  number: number;
  text: string;
  corrupted_text?: string | null;
  initial_status: InitialRuleStatus;
  source_style: RuleHand;
  is_ai_flaggable: boolean;
  display_order?: number;
}

export type SheetRuleUpdate = Partial<Omit<SheetRuleCreate, "key">>;

export interface SheetRuleResponse {
  rule_id: string;
  scenario_id: string;
  key: string;
  number: number;
  text: string;
  corrupted_text: string | null;
  initial_status: InitialRuleStatus;
  source_style: RuleHand;
  is_ai_flaggable: boolean;
  display_order: number;
}

export interface SheetRuleListResponse {
  items: SheetRuleResponse[];
}
