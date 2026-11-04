export type SceneKind = "negotiation" | "event" | "other";

export type SceneLifecycle = "pending" | "opened" | "resolved" | "defaulted";

export type TermsResult = "agreed" | "walked_out" | "refused";

export type PeaceTier = "short" | "medium" | "generation" | "perpetual";

export interface NonAggressionTerm {
  kind: "non_aggression";
  faction_a: string;
  faction_b: string;
  duration_turns: number;
}

export interface PeaceTerm {
  kind: "peace";
  faction_a: string;
  faction_b: string;
  tier: PeaceTier;
  duration_turns?: number;
  guarantor_ids?: string[];
}

export interface CedeRegionTerm {
  kind: "cede_region";
  from_faction_id?: string;
  from_faction?: string;
  to_faction_id?: string;
  to_faction?: string;
  region_id: string;
  region_name?: string;
}

export interface PayGoldTerm {
  kind: "pay_gold";
  payer_id: string;
  payee_id: string;
  amount: number;
}

export interface TributeTerm {
  kind: "tribute";
  payer_id: string;
  payee_id: string;
  gold_per_turn: number;
  duration_turns: number;
}

export interface ReleasePrisonersTerm {
  kind: "release_prisoners";
  holder_id: string;
  recipient_id?: string;
  target_id?: string;
  prisoner_ids?: string[];
  character_ids?: string[];
  ransom_gold?: number;
}

export interface HostageTerm {
  kind: "hostage";
  giver_id: string;
  holder_id?: string;
  receiver_id?: string;
  leader_id?: string;
  character_id?: string;
  character_name?: string;
  duration_turns?: number;
}

export interface TradeDealTerm {
  kind: "trade_deal";
  faction_a: string;
  faction_b: string;
  duration_turns: number;
}

export interface MilitaryAccessTerm {
  kind: "military_access";
  grantor_id: string;
  grantee_id: string;
  duration_turns: number;
}

export type PromiseKind =
  | "never_attack_faction"
  | "never_ally_with"
  | "spare_prisoners"
  | "never_occupy_region";

export interface SwornPromiseTerm {
  kind: "sworn_promise";
  promisor_id: string;
  beneficiary_id: string;
  promise: PromiseKind;
  subject_id?: string | null;
  duration_turns: number;
}

export interface AllianceTerm {
  kind: "alliance";
  faction_a: string;
  faction_b: string;
  alliance_type?: "defensive" | "offensive";
  duration_turns: number;
  is_separate_peace_banned?: boolean;
}

export interface VassalTerm {
  kind: "vassal";
  overlord_id: string;
  vassal_id: string;
  tribute_share_percent: number;
  levy_share_percent?: number;
  duration_turns: number;
}

export type ConditionTemplate =
  | "treasury_below"
  | "treasury_above"
  | "stability_below"
  | "war_exhaustion_above"
  | "region_count_below"
  | "region_count_above"
  | "turn_after"
  | "owns_region"
  | "loses_region";

export interface ConditionClause {
  template: ConditionTemplate;
  faction_id: string;
  value: number;
  region_id?: string | null;
}

export type BaseTreatyTerm =
  | TradeDealTerm
  | MilitaryAccessTerm
  | SwornPromiseTerm
  | AllianceTerm
  | VassalTerm
  | NonAggressionTerm
  | PeaceTerm
  | CedeRegionTerm
  | PayGoldTerm
  | TributeTerm
  | ReleasePrisonersTerm
  | HostageTerm;

export interface ConditionalTerm {
  kind: "conditional";
  mode: "trigger" | "gate";
  when: ConditionClause;
  expires_in_turns: number;
  inner: BaseTreatyTerm;
}

export type TreatyTerm =
  | ConditionalTerm
  | TradeDealTerm
  | MilitaryAccessTerm
  | SwornPromiseTerm
  | AllianceTerm
  | VassalTerm
  | NonAggressionTerm
  | PeaceTerm
  | CedeRegionTerm
  | PayGoldTerm
  | TributeTerm
  | ReleasePrisonersTerm
  | HostageTerm;

export interface TermsCard {
  proposer_id: string;
  counterpart_id: string;
  terms: TreatyTerm[];
  is_confirmed_by_player: boolean;
  is_confirmed_by_counterpart: boolean;
}

export interface RefusedDemand {
  terms_card: TermsCard;
  tone_grade: number;
}

export interface TermsCardOutcome {
  kind: "terms_card";
  result: TermsResult;
  terms_card?: TermsCard | null;
  refused_demand?: RefusedDemand | null;
}

export interface ChoiceSceneOutcome {
  kind: "choice";
  option_id: string;
}

export interface OtherSceneOutcome {
  kind: "grades" | "verdict" | "prose_only";
}

export interface JudgmentSceneOutcome {
  kind: "judgment";
  verdict: string;
  nuance: string | null;
}

export type SceneOutcome =
  | TermsCardOutcome
  | ChoiceSceneOutcome
  | JudgmentSceneOutcome
  | OtherSceneOutcome;

export interface SceneFact {
  label: string;
  value: string;
}

export interface SceneParticipant {
  participant_id: string;
  kind: string;
  name: string;
  trait_ids: string[];
  avatar_url?: string | null;
  stance?: "mercy" | "iron" | "neutral" | null;
}

export type TreatyVerdict = "accept" | "haggle" | "refuse";

export type ClauseWeightBand = "light" | "moderate" | "heavy";

export interface SceneExchange {
  sequence: number;
  player_text: string;
  leader_text: string;
  proposal?: TermsCard | null;
  verdict?: TreatyVerdict | null;
  clause_bands?: ClauseWeightBand[];
}

export type SceneInitiator = "player" | "ai";

export interface SceneDecisionInput {
  isConfirmed: boolean;
  proposalSequence?: number;
}

export type GrudgeBand = "faint" | "firm" | "burning";

export interface VoicedGrudge {
  text: string;
  band: GrudgeBand;
  is_inherited: boolean;
  predecessor_name: string | null;
}

export interface SceneViewResponse {
  scene_id: string;
  scene_type: string;
  status: SceneLifecycle;
  turn: number;
  initiator?: SceneInitiator;
  is_declinable?: boolean;
  situation: { summary: string; facts: SceneFact[] };
  participants: SceneParticipant[];
  transcript: SceneExchange[];
  exchanges_remaining: number;
  pending_proposal?: TermsCard | null;
  pending_proposal_sequence?: number | null;
  outcome?: SceneOutcome | null;
  voiced_grudges?: VoicedGrudge[];
  outcome_summary?: string[];
}

export interface PactView {
  commitment_id: string;
  faction_a: string;
  faction_b: string;
  start_turn: number;
  end_turn: number;
}

export interface StrategyDiplomacyProps {
  pacts: PactView[];
  isProposalAvailable: boolean;
  onProposeTerms: (factionId: string) => void;
}
