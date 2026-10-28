import type { PactView } from "./scene.types";

export interface IntRange {
  low: number;
  high: number;
}

export type TroopType = "infantry" | "cavalry" | "archers_siege";
export type TaxRate = "low" | "normal" | "high";
export type RouteStyle = "fastest" | "safest" | "roads";
export type ImprovementKind =
  | "farms_and_market"
  | "fort"
  | "barracks"
  | "roads"
  | "temple";

export interface ImprovementState {
  kind: ImprovementKind;
  turns_remaining: number;
}

export interface RegionDetail {
  id: string;
  owner_id: string | null;
  population: number;
  wealth: number;
  manpower: number;
  unrest: number;
  garrison: number;
  faith_id: string | null;
  improvements: ImprovementState[];
  governor_id?: string | null;
  claimant_ids: string[];
  conversion_turns_remaining: number;
}

export interface RegionView {
  region_id: string;
  owner_id: string | null;
  terrain: string;
  visibility: "visible" | "fogged";
  last_seen_turn?: number | null;
  garrison_estimate?: IntRange | null;
  detail?: RegionDetail | null;
}

export interface ArmyView {
  army_id: string;
  owner_id: string;
  location_id: string;
  commander_name?: string | null;
  size_estimate?: IntRange | null;
  troops?: Partial<Record<TroopType, number>> | null;
}

export interface RivalView {
  faction_id: string;
  name: string;
  leader_name?: string | null;
  relation: string;
  treasury_range: IntRange;
  manpower_range: IntRange;
}

export interface LoanState {
  principal: number;
  interest_percent: number;
  turns_remaining: number;
}

export interface OwnFactionView {
  id: string;
  leader_id?: string | null;
  treasury: number;
  manpower: number;
  stability: number;
  war_exhaustion: number;
  reputation: number;
  tax_rate: TaxRate;
  loans: LoanState[];
}

export interface TurnClock {
  turn: number;
  start_year: number;
  start_month: number;
}

export interface RulerView {
  name: string;
  epithet?: string | null;
  portrait_url?: string | null;
}

export interface MoveArmyOrder {
  kind: "move_army";
  faction_id: string;
  army_id: string;
  to_region_id: string;
  route_style?: RouteStyle;
  via_region_ids?: string[];
  avoid_region_ids?: string[];
}

export interface HaltArmyOrder {
  kind: "halt_army";
  faction_id: string;
  army_id: string;
}

export interface AttackOrder {
  kind: "attack";
  faction_id: string;
  army_id: string;
  target_region_id: string;
}

export interface RaiseArmyOrder {
  kind: "raise_army";
  faction_id: string;
  region_id: string;
  troops: Partial<Record<TroopType, number>>;
}

export interface DisbandArmyOrder {
  kind: "disband_army";
  faction_id: string;
  army_id: string;
}

export interface SetTaxRateOrder {
  kind: "set_tax_rate";
  faction_id: string;
  tax_rate: TaxRate;
}

export interface TakeLoanOrder {
  kind: "take_loan";
  faction_id: string;
  amount: number;
}

export interface BuildImprovementOrder {
  kind: "build_improvement";
  faction_id: string;
  region_id: string;
  improvement_kind: ImprovementKind;
}

export type EconomyChoice = "shortfall_take_loan" | "shortfall_default";

export interface AnswerEventOrder {
  kind: "answer_event";
  faction_id: string;
  event_id: string;
  choice_id: string;
}

export type UprisingResponseId = "concessions" | "restore_order" | "negotiate";
export type UprisingArchetype = "petition" | "riot" | "rebellion";
export type UprisingStage = "unrest" | "riot" | "armed";

export interface ResolveUprisingOrder {
  kind: "resolve_uprising";
  faction_id: string;
  uprising_id: string;
  response: UprisingResponseId;
}

export type StrategyOrder =
  | AnswerEventOrder
  | ResolveUprisingOrder
  | MoveArmyOrder
  | HaltArmyOrder
  | AttackOrder
  | RaiseArmyOrder
  | DisbandArmyOrder
  | SetTaxRateOrder
  | TakeLoanOrder
  | BuildImprovementOrder;

export interface BattleControlCommand {
  kind: "take_command" | "delegate_battle";
  faction_id: string;
  battle_id: string;
}

export type StrategyCommand = StrategyOrder | BattleControlCommand;

export interface QueuedOrderView {
  id: string;
  order: StrategyOrder;
  cost: number;
  queued_turn: number;
  is_cancellable: boolean;
}

export type CampaignStatus =
  | "planning"
  | "awaiting_commands"
  | "awaiting_battle_decision"
  | "awaiting_scene"
  | "turn_completed";

export interface BattleView {
  id: string;
  region_id: string;
  status: string;
  outcome?: string | null;
  exchanges_used: number;
  total_exchanges: number;
  is_big?: boolean;
  control_mode?: "undecided" | "player" | "delegated";
  current_turn?: number;
}

export interface SceneRef {
  scene_id: string;
  scene_type: string;
}

export type SummaryTrigger = "major_event" | "significance";
export type SummaryStatus = "pending" | "generating" | "completed" | "failed";

export interface StrategySummaryView {
  summary_id: string;
  requested_turn: number;
  trigger: SummaryTrigger;
  status: SummaryStatus;
  narration?: string | null;
  error_code?: string | null;
  is_retryable: boolean;
  region_ids: string[];
}

export interface StrategySummaryPage {
  items: StrategySummaryView[];
  next_after_id?: string | null;
}

export interface SummaryAvailability {
  pending_count: number;
  latest_summary_id?: string | null;
}

export type EventSubjectKind = "region" | "governor" | "army" | "faction" | "leader";

export interface EffectPreviewView {
  kind: string;
  amount: number;
}

export interface EventChoiceView {
  id: string;
  label_hint: string;
  order_cost: number;
  effects: EffectPreviewView[];
  is_affordable: boolean;
}

export interface PendingEventView {
  id: string;
  template_id: string;
  name: string;
  subject_kind: EventSubjectKind;
  subject_id: string;
  subject_name: string;
  region_id?: string | null;
  tier: number;
  max_tier: number;
  created_turn: number;
  deadline_turn: number;
  cause_key: string;
  cause_inputs: Record<string, number>;
  choices: EventChoiceView[];
  neglect_effects: EffectPreviewView[];
  queued_choice_id?: string | null;
  queued_command_id?: string | null;
}

export interface EventMemoryView {
  template_id: string;
  name: string;
  subject_id: string;
  subject_name: string;
  region_id?: string | null;
  last_tier: number;
  max_tier: number;
  scar: number;
}

export type EndingKind = "victory" | "defeat" | "graded";

export interface EndingView {
  ending_id: string;
  kind: EndingKind;
  turn: number;
}

export interface UprisingResponseView {
  id: UprisingResponseId;
  order_cost: number;
  effects: EffectPreviewView[];
  notes: string[];
  is_affordable: boolean;
}

export interface UprisingView {
  id: string;
  region_id: string;
  faction_id: string;
  started_turn: number;
  trigger_unrest: number;
  income_penalty_percent: number;
  manpower_penalty_percent: number;
  supply_penalty_percent: number;
  archetype: UprisingArchetype;
  stage: UprisingStage;
  turns_in_stage: number;
  easing_turns: number;
  responses: UprisingResponseView[];
  turns_until_change: number;
  is_final_stage: boolean;
  is_easing: boolean;
  rebel_troops: number | null;
  queued_response: UprisingResponseId | null;
  queued_command_id: string | null;
}

export interface CampaignWorldView {
  playthrough_id?: string;
  world_version: number;
  world_hash?: string;
  turn: number;
  wave: number;
  status: CampaignStatus;
  battles: BattleView[];
  scene_id?: string | null;
  clock: TurnClock;
  my_faction: OwnFactionView;
  ruler: RulerView;
  regions: RegionView[];
  armies: ArmyView[];
  rivals: RivalView[];
  pacts?: PactView[];
  queued_orders: QueuedOrderView[];
  orders_remaining: number;
  pending_events?: PendingEventView[];
  uprisings?: UprisingView[];
  event_memories?: EventMemoryView[];
  pending_scene?: SceneRef | null;
  ending?: EndingView | null;
  summary_availability?: SummaryAvailability;
}

export type OrderFlag = "over_budget" | "impossible" | "not_your_army";

export interface OrderCheckResponse {
  flag?: OrderFlag | null;
  reason?: string | null;
  orders_remaining: number;
}

export interface OperationGuard {
  operation_id: string;
  expected_world_version: number;
  expected_turn: number;
  expected_wave: number;
}

export interface MutationResponse {
  playthrough_id: string;
  world_version: number;
  world_hash: string;
  turn: number;
  wave: number;
  orders_remaining: number;
  status: CampaignStatus;
  battles: BattleView[];
  scene_id?: string | null;
  operation_id: string;
  accepted_command_id?: string | null;
}
