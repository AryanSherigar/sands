type NewFeatureTarget =
  | { kind: "guide-step"; stepNumber: number }
  | { kind: "card" };

export interface NewFeature {
  id: string;
  name: string;
  description: string;
  releasedOn: string;
  location: string;
  example: string;
  isAdvanced: boolean;
  target: NewFeatureTarget;
}

const LAUNCH_RELEASE_DATE = "2026-10-28";
const ADVANCED_RELEASE_DATE = "2026-10-29";

export const NEW_FEATURES: readonly NewFeature[] = [
  {
    id: "triggers",
    name: "Triggers",
    description: "Words that bring a card into the scene.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Open any card and look under Triggers.",
    example: "Mara's card lists “the keeper”. When a player says “talk to the keeper”, the narrator recalls Mara.",
    isAdvanced: false,
    target: { kind: "card" },
  },
  {
    id: "links",
    name: "Links",
    description: "Connect two cards with a short sentence that shows on both.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Open any card and look under Links.",
    example: "“Mara guards The Lighthouse” appears on Mara's card and on The Lighthouse's card.",
    isAdvanced: false,
    target: { kind: "card" },
  },
  {
    id: "always-remember",
    name: "Always remember",
    description: "Short rules the narrator keeps in mind every turn.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Guide, step 5 World, under your world description.",
    example: "“Nobody can lie inside the lighthouse.” stays true in every scene.",
    isAdvanced: false,
    target: { kind: "guide-step", stepNumber: 5 },
  },
  {
    id: "storytelling-style",
    name: "Storytelling style",
    description: "Choose how the narrator tells your story.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Guide, step 6 Opening, under Storytelling style.",
    example: "Pick Cozy for warm, gentle scenes, or Dark & gritty for a harsher tone.",
    isAdvanced: false,
    target: { kind: "guide-step", stepNumber: 6 },
  },
  {
    id: "player-step",
    name: "Player step",
    description: "Decide who the player is, or let them create their own character.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Guide, step 3 Player.",
    example: "Write the player as a lighthouse keeper, or let each player choose a name and background.",
    isAdvanced: false,
    target: { kind: "guide-step", stepNumber: 3 },
  },
  {
    id: "questions-to-help",
    name: "Questions to Help",
    description: "Folded prompts under each box that turn answers into your text.",
    releasedOn: LAUNCH_RELEASE_DATE,
    location: "Guide, step 2 Premise, under the premise box.",
    example: "Answer “What stands in their way?” and the answer becomes a linked line in your premise.",
    isAdvanced: false,
    target: { kind: "guide-step", stepNumber: 2 },
  },
  {
    id: "advanced-mode",
    name: "Advanced mode",
    description: "One switch that adds endings, tracked values, rules and hard limits to any story.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Your story list, at the bottom, or the invitation after Opening.",
    example: "Turn it on, add Health, and end the story when Health drops to 0. Turn it off anytime and nothing is lost.",
    isAdvanced: true,
    target: { kind: "guide-step", stepNumber: 6 },
  },
  {
    id: "endings",
    name: "Endings",
    description: "Say when your story ends and what the player reads.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Guide, Endings, after Opening (Advanced mode).",
    example: "A Lose ending that fires when Lantern oil drops to 0 and tells the keeper the light has gone out.",
    isAdvanced: true,
    target: { kind: "guide-step", stepNumber: 7 },
  },
  {
    id: "tracked-values",
    name: "Tracked values",
    description: "Things the story keeps count of, like Health, Trust or Time.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Guide, Tracked values (Advanced mode).",
    example: "Add Trust from 0 to 10, starting at 5, and show it to the player as a bar.",
    isAdvanced: true,
    target: { kind: "guide-step", stepNumber: 8 },
  },
  {
    id: "rules",
    name: "Rules",
    description: "React to your tracked values: guide the narrator, change values, or both.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Guide, Rules (Advanced mode).",
    example: "When Trust is at least 8, tell the narrator that Mara shares her secret.",
    isAdvanced: true,
    target: { kind: "guide-step", stepNumber: 9 },
  },
  {
    id: "hard-limits",
    name: "Hard limits",
    description: "Say what can never happen, so a change that breaks it is blocked.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Guide, Hard limits (Advanced mode).",
    example: "Health is at most Max health. While in the chapel, the weapon must stay sheathed.",
    isAdvanced: true,
    target: { kind: "guide-step", stepNumber: 10 },
  },
  {
    id: "card-values",
    name: "Card values",
    description: "Give a character, place or thing its own numbers and yes / no facts.",
    releasedOn: ADVANCED_RELEASE_DATE,
    location: "Open any card and look under Values (Advanced mode).",
    example: "Mara's Trust is 70. An ending or rule can then use “Mara's Trust”.",
    isAdvanced: true,
    target: { kind: "card" },
  },
];

export const FEATURE_HIGHLIGHT_MS = 300;
export const NEW_FEATURES_LABEL = "New features";
export const NO_NEW_FEATURES_MESSAGE = "Nothing new since you made this story.";
export const ADVANCED_FEATURE_LABEL = "Advanced mode";
export const ADVANCED_FEATURE_HINT = "Turn on Advanced mode to use this.";
