import { MAX_MOOD_TAGS, MAX_MOOD_TAG_LENGTH } from "../constants/guideLimits";

export const toggleTag = (tags: string[], tag: string): string[] =>
  tags.includes(tag) ? tags.filter((existing) => existing !== tag) : [...tags, tag];

export const addCustomMood = (moods: string[], rawMood: string): string[] => {
  const mood = rawMood.trim().toLowerCase().slice(0, MAX_MOOD_TAG_LENGTH);
  if (!mood || moods.includes(mood) || moods.length >= MAX_MOOD_TAGS) return moods;
  return [...moods, mood];
};
