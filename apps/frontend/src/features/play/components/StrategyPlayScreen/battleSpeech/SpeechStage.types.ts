import type { ArmyMood, CrowdReaction } from "../../../types/battleSpeech.types";

export interface SpeechStageProps {
  mood: ArmyMood;
  reaction: CrowdReaction | null;
}
