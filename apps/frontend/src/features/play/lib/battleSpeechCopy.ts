import type {
  CrowdIntensity,
  CrowdMood,
  CrowdReaction,
  SpeechTalkIndex,
} from "../types/battleSpeech.types";

export const TALK_LABELS: Record<SpeechTalkIndex, string> = {
  1: "Opening talk",
  2: "Middle talk",
  3: "Closing talk",
};

const REACTION_CAPTIONS: Record<CrowdMood, Record<CrowdIntensity, string>> = {
  hush: {
    1: "The ranks go quiet.",
    2: "A hush falls over the ranks.",
    3: "The whole army stands utterly still.",
  },
  murmur: {
    1: "A low murmur runs through the ranks.",
    2: "The men murmur among themselves.",
    3: "A restless murmur swells and will not settle.",
  },
  protest: {
    1: "Some men mutter and shift their feet.",
    2: "The crowd jeers.",
    3: "The ranks erupt in angry protest.",
  },
  cheer: {
    1: "A few voices raise a cheer.",
    2: "The crowd cheers.",
    3: "The army roars its approval.",
  },
};

export const describeReaction = (reaction: CrowdReaction): string =>
  REACTION_CAPTIONS[reaction.mood][reaction.intensity];

export function describeMoraleChange(moralePercent: number): string {
  if (moralePercent > 0) {
    return `Your words steadied the army: morale rose by ${moralePercent}%.`;
  }
  if (moralePercent < 0) {
    return `Your words fell flat: morale fell by ${Math.abs(moralePercent)}%.`;
  }
  return "The army heard you out, and its spirits are unchanged.";
}
