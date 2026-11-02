export type JudgmentVerdictId = "release" | "exile" | "imprison" | "execute";

export type JudgmentNuanceId =
  | "with_warning"
  | "under_oath"
  | "with_pardon"
  | "with_fine"
  | "beyond_border"
  | "stripped_of_title"
  | "with_family"
  | "with_price_on_return"
  | "in_region"
  | "in_capital"
  | "for_a_term"
  | "for_life"
  | "quietly"
  | "publicly"
  | "swiftly"
  | "with_last_word";

export type JudgmentStance = "mercy" | "iron" | "neutral";

export type JudgmentSubjectKind = "captive" | "governor";

export interface JudgmentCourtMember {
  participantId: string;
  name: string;
  kind: string;
  stance: JudgmentStance | null;
}

export interface JudgmentExchange {
  sequence: number;
  playerText: string;
  courtText: string;
}

export interface JudgmentPronouncement {
  verdict: JudgmentVerdictId;
  nuance: JudgmentNuanceId | null;
  decreeText: string;
}

export interface StrategyJudgmentPackage {
  sceneId: string;
  turn: number;
  summary: string;
  charge: string;
  subjectKind: JudgmentSubjectKind;
  accused: JudgmentCourtMember;
  advisors: JudgmentCourtMember[];
  openingText: string;
  exchanges: JudgmentExchange[];
  spokenExchangesRemaining: number;
  outcomeSummary: string[];
  isResolved: boolean;
}
