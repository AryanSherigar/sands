import type { MutationResponse, OperationGuard } from "./simulation.types";

export type CrowdMood = "hush" | "murmur" | "protest" | "cheer";
export type CrowdIntensity = 1 | 2 | 3;
export type MoraleBucket = "broken" | "shaken" | "steady" | "resolute" | "fervent";
export type ExhaustionBucket = "fresh" | "tired" | "spent";
export type PayBucket = "paid" | "grumbling" | "unpaid";
export type BattleSpeechStatus = "pending" | "done";
export type SpeechTalkIndex = 1 | 2 | 3;

export interface CrowdReaction {
  mood: CrowdMood;
  intensity: CrowdIntensity;
}

export interface ArmyMood {
  morale: MoraleBucket;
  exhaustion: ExhaustionBucket;
  pay: PayBucket;
}

export interface BattleSpeechOutcome {
  kind: "battle_speech";
  morale_delta_percent: number;
  rubric_scores: Record<string, number>;
}

export interface SpeechView {
  status: BattleSpeechStatus;
  officer_report: string;
  mood: ArmyMood;
  next_talk: SpeechTalkIndex | null;
  reactions: CrowdReaction[];
  outcome: BattleSpeechOutcome | null;
}

export interface SpeechTalkRequest {
  guard: OperationGuard;
  talk_index: SpeechTalkIndex;
  text: string;
}

export interface SpeechTalkResult {
  reaction: CrowdReaction;
  is_complete: boolean;
  morale_delta_percent: number | null;
  state: MutationResponse;
}

export interface SubmitSpeechTalkInput {
  talkIndex: SpeechTalkIndex;
  text: string;
}
