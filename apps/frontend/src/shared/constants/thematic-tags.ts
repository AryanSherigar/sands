import {
  IconBrain,
  IconBuildingBank,
  IconCloudStorm,
  IconDroplet,
  IconFileSearch,
  IconFlame,
  IconGhost,
  IconHeart,
  IconMessage2Exclamation,
  IconMoodCrazyHappy,
  IconMug,
  IconScale,
  IconSwords,
  IconUsers,
} from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

export const MAX_THEMATIC_TAGS = 5;

export interface ThematicTagDefinition {
  id: string;
  label: string;
  explanation: string;
  Icon: Icon;
}

// NOTE: Ids mirror CONTENT_TAG_VOCABULARY in apps/core-api/app/models/content_tags.py.
// The API rejects any id not in that list, so keep the two in step.
export const THEMATIC_TAGS: readonly ThematicTagDefinition[] = [
  {
    id: "noir-atmosphere",
    label: "Noir atmosphere",
    explanation: "Rain, shadow-sm and cynical, hard-boiled narration.",
    Icon: IconDroplet,
  },
  {
    id: "moral-ambiguity",
    label: "Moral ambiguity",
    explanation: "No clean heroic answers; most choices carry a cost.",
    Icon: IconScale,
  },
  {
    id: "investigation",
    label: "Investigation",
    explanation: "Progress comes from gathering clues and following leads.",
    Icon: IconFileSearch,
  },
  {
    id: "political-intrigue",
    label: "Political intrigue",
    explanation: "Factions, favours and quiet betrayals drive the plot.",
    Icon: IconBuildingBank,
  },
  {
    id: "survival-pressure",
    label: "Survival pressure",
    explanation: "Scarce resources and constant danger.",
    Icon: IconFlame,
  },
  {
    id: "psychological-tension",
    label: "Psychological tension",
    explanation: "Dread and unease build more than open action.",
    Icon: IconBrain,
  },
  {
    id: "cozy-tone",
    label: "Cozy tone",
    explanation: "Low stakes and a warm, gentle mood.",
    Icon: IconMug,
  },
  {
    id: "dark-humour",
    label: "Dark humour",
    explanation: "Grim situations played for wry or absurd laughs.",
    Icon: IconMoodCrazyHappy,
  },
  {
    id: "romance",
    label: "Romance",
    explanation: "Romantic relationships are a meaningful thread.",
    Icon: IconHeart,
  },
  {
    id: "found-family",
    label: "Found family",
    explanation: "Companions become a chosen family.",
    Icon: IconUsers,
  },
  {
    id: "graphic-violence",
    label: "Graphic violence",
    explanation: "Contains explicit depictions of violence.",
    Icon: IconSwords,
  },
  {
    id: "strong-language",
    label: "Strong language",
    explanation: "Contains profanity.",
    Icon: IconMessage2Exclamation,
  },
  {
    id: "horror-themes",
    label: "Horror themes",
    explanation: "Contains frightening or disturbing content.",
    Icon: IconGhost,
  },
  {
    id: "heavy-themes",
    label: "Heavy themes",
    explanation: "Deals with grief, loss or other difficult subjects.",
    Icon: IconCloudStorm,
  },
];

export const getThematicTag = (
  id: string,
): ThematicTagDefinition | undefined =>
  THEMATIC_TAGS.find((tag) => tag.id === id);
