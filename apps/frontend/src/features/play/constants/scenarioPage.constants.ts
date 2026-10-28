import {
  IconDice5,
  IconMap2,
  IconPuzzle,
  IconUsersGroup,
} from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

export const LORE_COLLAPSED_LINES_CLASS = "line-clamp-12";

export const SHARE_COPIED_MESSAGE = "Link copied";

export const REVIEWS_SECTION_ID = "scenario-reviews";
export const MIN_TURNS_TO_REVIEW = 10;
export const REVIEWS_PAGE_SIZE = 10;

export const MODE_LABELS: Record<string, string> = {
  newbie: "Simple",
  master: "Advanced",
};

export const COMPLEXITY_LABELS: Record<string, string> = {
  newbie: "Beginner",
  intermediate: "Intermediate",
  master: "Expert",
};

export interface MechanicalChipDefinition {
  id: string;
  label: string;
  explanation: string;
  Icon: Icon;
}

export const DICE_CHIP: MechanicalChipDefinition = {
  id: "dice-and-stat-resolution",
  label: "Dice & stat resolution",
  explanation:
    "Risky actions are resolved with dice rolls against your character's stats.",
  Icon: IconDice5,
};

export const MAP_CHIP: MechanicalChipDefinition = {
  id: "map-exploration",
  label: "Map exploration",
  explanation: "Travel between places on an interactive map.",
  Icon: IconMap2,
};

export const MINIGAME_CHIP: MechanicalChipDefinition = {
  id: "minigames",
  label: "Minigames",
  explanation: "Some moments are played out as short skill challenges.",
  Icon: IconPuzzle,
};

export const MULTIPLAYER_CHIP: MechanicalChipDefinition = {
  id: "multiplayer-capable",
  label: "Multiplayer-capable",
  explanation: "You can invite others to join your run.",
  Icon: IconUsersGroup,
};

export const MATURE_CHIP_LABEL = "Mature themes";
export const MATURE_CHIP_EXPLANATION =
  "Contains content intended for mature audiences.";

export const ADVANCED_MODE = "master";
export const MULTIPLAYER_SUPPORT_VALUES: readonly string[] = [
  "multiplayer",
  "both",
];

export const OUTCOME_LABELS: Record<"win" | "lose", string> = {
  win: "Victory",
  lose: "Defeat",
};
