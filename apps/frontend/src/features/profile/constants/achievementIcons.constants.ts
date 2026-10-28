import {
  IconAward,
  IconBook,
  IconBooks,
  IconChecklist,
  IconCompass,
  IconCrown,
  IconDoorExit,
  IconEye,
  IconFeather,
  IconFlag,
  IconHammer,
  IconMap2,
  IconRoute,
  IconStar,
  IconTrophy,
  IconUsers,
  IconWalk,
  IconWorld,
  type TablerIcon,
} from "@tabler/icons-react";

export const ACHIEVEMENT_ICONS: Record<string, TablerIcon> = {
  "first-steps": IconFlag,
  "final-page": IconBook,
  wayfarer: IconWalk,
  voyager: IconRoute,
  chronicler: IconFeather,
  "genre-curious": IconCompass,
  "every-shelf": IconBooks,
  "five-worlds": IconWorld,
  "far-traveller": IconMap2,
  "an-ending": IconDoorExit,
  triumph: IconTrophy,
  "every-ending": IconChecklist,
  worldmaker: IconHammer,
  "first-readers": IconEye,
  crowd: IconUsers,
  beloved: IconCrown,
  "five-stars": IconStar,
};

export const getAchievementIcon = (key: string): TablerIcon =>
  ACHIEVEMENT_ICONS[key] ?? IconAward;
