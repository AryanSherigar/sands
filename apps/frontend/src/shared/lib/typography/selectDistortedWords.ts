import { seededUnit } from "@/shared/lib/hud/seededUnit";

const DISTORTED_WORD_RATIO = 0.05;
const MIN_DISTORTABLE_LETTERS = 3;
const WORD_PATTERN = /\S+/g;
const LETTER_PATTERN = /[\p{L}\p{N}]/gu;

export interface WordToken {
  index: number;
  start: number;
  end: number;
}

export interface DistortionOptions {
  paragraphIndex?: number;
  protectedRanges?: readonly (readonly [number, number])[];
  isComplete?: boolean;
}

export function findWords(text: string): WordToken[] {
  const words: WordToken[] = [];
  for (const match of text.matchAll(WORD_PATTERN)) {
    const start = match.index ?? 0;
    words.push({ index: words.length, start, end: start + match[0].length });
  }
  return words;
}

const countLetters = (word: string): number => word.match(LETTER_PATTERN)?.length ?? 0;

const overlapsRange = (
  word: WordToken,
  ranges: readonly (readonly [number, number])[],
): boolean => ranges.some(([start, end]) => word.start < end && word.end > start);

// Word indices (whitespace-separated, counted from 0) that render in the eerie
// face. The draw is seeded by playthrough, turn, paragraph and word index only,
// never by the text, so indices are prefix-stable while a paragraph streams in.
// Words of two letters or fewer and words overlapping a protected range (entity
// highlights) are never picked. While `isComplete` is false the last word may
// still be arriving, so it is skipped until a space follows it.
export function selectDistortedWords(
  text: string,
  playthroughId: string,
  turnNumber: number,
  options: DistortionOptions = {},
): Set<number> {
  const { paragraphIndex = 0, protectedRanges = [], isComplete = true } = options;
  const seed = `${playthroughId}:${turnNumber}:${paragraphIndex}`;
  const hasTrailingSpace = /\s$/.test(text);
  const words = findWords(text);
  const selected = new Set<number>();
  for (const word of words) {
    const isLastUnfinished =
      !isComplete && !hasTrailingSpace && word.index === words.length - 1;
    const isDistortable =
      countLetters(text.slice(word.start, word.end)) >= MIN_DISTORTABLE_LETTERS &&
      !isLastUnfinished &&
      !overlapsRange(word, protectedRanges);
    if (isDistortable && seededUnit(seed, word.index) < DISTORTED_WORD_RATIO) {
      selected.add(word.index);
    }
  }
  return selected;
}
