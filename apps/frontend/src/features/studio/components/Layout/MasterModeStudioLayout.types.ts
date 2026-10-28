import type { ToolKey } from "@/shared/constants/scenario-tools";

interface MasterModeTabDefinition {
  id: string;
  label: string;
  helpText: string;
  tool?: ToolKey;
}

export const MASTER_MODE_TABS = [
  {
    id: "entities",
    label: "People, Places & Things",
    helpText:
      "Entities are the characters, locations, items, and factions the narrator can reference. Give each one a name and, optionally, tracked attributes.",
  },
  {
    id: "facts",
    label: "What's True",
    helpText:
      'Facts are statements the narrator checks and respects during play, e.g. "Hero → owns → Sword". They can link two entities or attach a note to a single one.',
  },
  {
    id: "state",
    label: "Tracked Values",
    helpText:
      "Tracked values are the numbers, flags, and variables that change as the story plays out — health, gold, faction standing, and the like.",
  },
  {
    id: "conditions",
    label: "Active Rules",
    helpText:
      "Active rules watch tracked values and entity facts during play and trigger narrator behavior when they become true.",
  },
  {
    id: "invariants",
    label: "Always-True Rules",
    helpText:
      "Always-true rules are constraints the narrator must never violate, regardless of what else happens in the story.",
  },
  {
    id: "endings",
    label: "Win & Lose Conditions",
    helpText:
      "Win and lose conditions define how a playthrough concludes. Each one has an outcome, a message shown to the player, and an optional trigger.",
  },
  {
    id: "minigames",
    label: "Minigames",
    helpText:
      "Minigames trigger a full-screen interstitial challenge — a curated dodge arena — whose outcome mutates state and feeds back into the narration. Solo playthroughs only.",
  },
  {
    id: "rule_checks",
    label: "Rule checks",
    tool: "rule_checks",
    helpText:
      "Rule checks are timed prompts the game opens from tracked values. The player's answer is written back into a tracked value that your active rules can react to.",
  },
  {
    id: "rule_sheet",
    label: "Rule sheet",
    tool: "rule_sheet",
    helpText:
      "The rules on the player's clipboard. A rule's status changes through active rules that set rule_status.<key>.",
  },
  {
    id: "hud",
    label: "HUD",
    tool: "status_hud",
    helpText:
      "Choose which tracked values appear as a clock, a meter or a tension tier on the play screen.",
  },
  {
    id: "atmosphere",
    label: "Atmosphere",
    tool: "atmosphere",
    helpText:
      "Sound cues, reader effects that grow with a meter, and the music that follows the tension tier.",
  },
  {
    id: "maps",
    label: "Maps",
    helpText:
      "Draw maps and pin your Location entities onto them, then connect locations together. Connections are advisory only — they inform the narrator, they never restrict where the player can go.",
  },
  {
    id: "music",
    label: "Mood Music",
    helpText:
      "Upload or generate a track for each of the 6 moods your narrator can call for. Any mood left unset automatically falls back to its default track.",
  },
  {
    id: "tools",
    label: "Tools",
    helpText:
      "Tools are optional extras for stories that need them, such as timed prompts, a status display or atmosphere. A story with no tools plays exactly as before.",
  },
  {
    id: "setup",
    label: "Setup & Narrator",
    helpText:
      "Configure the scenario's metadata, opening scene, narrator persona, and other one-time setup details here.",
  },
] as const satisfies readonly MasterModeTabDefinition[];

export type MasterModeTabId = (typeof MASTER_MODE_TABS)[number]["id"];

export interface MasterModeTab {
  id: MasterModeTabId;
  label: string;
  helpText: string;
  tool?: ToolKey;
}

export interface MasterModeStudioLayoutProps {
  scenarioId: string;
}

export interface StudioSetupPanelProps {
  scenarioId: string;
}

export interface MasterModeNavProps {
  scenarioId: string;
  tabs: readonly MasterModeTab[];
  activeTab: MasterModeTabId;
  onTabSelect: (tabId: MasterModeTabId) => void;
}

export interface MasterModeTabPanelsProps {
  scenarioId: string;
  activeTab: MasterModeTabId;
  visitedTabs: Set<MasterModeTabId>;
}
