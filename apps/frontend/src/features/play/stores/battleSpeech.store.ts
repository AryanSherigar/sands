import { create } from "zustand";
import type { CrowdReaction } from "../types/battleSpeech.types";

export type BattleSpeechPhase = "report" | "talking" | "reacting" | "result";

interface BattleSpeechState {
  phase: BattleSpeechPhase;
  lastReaction: CrowdReaction | null;
  beginTalking: () => void;
  showReaction: (reaction: CrowdReaction) => void;
  continueAfterReaction: (isComplete: boolean) => void;
  reset: () => void;
}

const INITIAL_STATE = { phase: "report" as BattleSpeechPhase, lastReaction: null };

export const useBattleSpeechStore = create<BattleSpeechState>((set) => ({
  ...INITIAL_STATE,
  beginTalking: () => set({ phase: "talking" }),
  showReaction: (reaction) => set({ phase: "reacting", lastReaction: reaction }),
  continueAfterReaction: (isComplete) => set({ phase: isComplete ? "result" : "talking" }),
  reset: () => set(INITIAL_STATE),
}));
