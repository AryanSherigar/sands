export type SceneKind = "negotiation" | "event" | "other";

export type SceneLifecycle = "pending" | "opened" | "resolved" | "defaulted";

export type TermsResult = "agreed" | "walked_out" | "refused";

export interface NonAggressionTerm {
  kind: "non_aggression";
  faction_a: string;
  faction_b: string;
  duration_turns: number;
}

export interface TermsCard {
  proposer_id: string;
  counterpart_id: string;
  terms: NonAggressionTerm[];
  is_confirmed_by_player: boolean;
  is_confirmed_by_counterpart: boolean;
}

export interface TermsCardOutcome {
  kind: "terms_card";
  result: TermsResult;
  terms_card?: TermsCard | null;
}

export interface OtherSceneOutcome {
  kind: "choice" | "grades" | "verdict" | "prose_only";
}

export type SceneOutcome = TermsCardOutcome | OtherSceneOutcome;

export interface SceneFact {
  label: string;
  value: string;
}

export interface SceneParticipant {
  participant_id: string;
  kind: string;
  name: string;
  trait_ids: string[];
}

export interface SceneExchange {
  sequence: number;
  player_text: string;
  leader_text: string;
  proposal?: TermsCard | null;
}

export type SceneInitiator = "player" | "ai";

export interface SceneDecisionInput {
  isConfirmed: boolean;
  proposalSequence?: number;
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
