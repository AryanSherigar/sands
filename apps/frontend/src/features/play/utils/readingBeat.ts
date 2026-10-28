import {
  MAX_READING_BEAT_MS,
  MIN_READING_BEAT_MS,
  READING_WORDS_PER_MINUTE,
} from "../constants/ruleCheck.constants";

const MS_PER_MINUTE = 60_000;

export function readingBeatMs(narrationText: string): number {
  const wordCount = narrationText.split(/\s+/).filter(Boolean).length;
  const readingMs = (wordCount / READING_WORDS_PER_MINUTE) * MS_PER_MINUTE;
  return Math.min(MAX_READING_BEAT_MS, Math.max(MIN_READING_BEAT_MS, readingMs));
}
