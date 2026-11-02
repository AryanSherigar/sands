import { IconCrown, IconGuitarPick, IconScale, IconScript, IconSword } from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

export interface Chronicler {
  id: string;
  name: string;
  title: string;
  tagline: string;
  avatarIcon: Icon;
  color: string;
}

export const CHRONICLERS: Chronicler[] = [
  {
    id: "lucan",
    name: "Brother Lucan",
    title: "Monastic Scribe",
    tagline: "Somber, pious, and morally serious; records the human toll of ambition.",
    avatarIcon: IconScript,
    color: "#46606E",
  },
  {
    id: "morvath",
    name: "Morvath of Highcourt",
    title: "Crown Loyalist",
    tagline: "Grand and heraldic; frames royal dominion as sovereign justice.",
    avatarIcon: IconCrown,
    color: "#A8483E",
  },
  {
    id: "teresa",
    name: "Lady Teresa of Valis",
    title: "Cynical Diplomat",
    tagline: "Dispassionate realpolitik; weighs power, coin, and leverage.",
    avatarIcon: IconScale,
    color: "#6B5B95",
  },
  {
    id: "salt_road_bard",
    name: "The Salt-Road Bard",
    title: "Folk Historian",
    tagline: "Vernacular and earthy; chronicles what ordinary folk endure.",
    avatarIcon: IconGuitarPick,
    color: "#8B5A2B",
  },
  {
    id: "vaelen",
    name: "Vaelen the Scorned",
    title: "Hostile Polemicist",
    tagline: "Irrationally despises your crown; frames every victory as butchery and tyranny.",
    avatarIcon: IconSword,
    color: "#8B0000",
  },
];

export const DEFAULT_CHRONICLER_ID = "lucan";

export function getChronicler(id?: string | null): Chronicler {
  return CHRONICLERS.find((c) => c.id === id) ?? CHRONICLERS[0];
}
