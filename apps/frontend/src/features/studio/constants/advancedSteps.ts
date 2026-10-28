import type { GuideStepDefinition } from "./guideSteps";

const FIRST_ADVANCED_STEP_NUMBER = 7;

export const ADVANCED_GUIDE_STEPS: readonly GuideStepDefinition[] = [
  {
    id: "endings",
    number: FIRST_ADVANCED_STEP_NUMBER,
    name: "Endings",
    header: "How can the story end?",
    helper: "Without endings, your story never ends — players can keep going.",
  },
  {
    id: "tracked_values",
    number: FIRST_ADVANCED_STEP_NUMBER + 1,
    name: "Tracked values",
    header: "What matters along the way?",
    helper:
      "Things the story keeps count of. The narrator changes them as the story happens.",
  },
  {
    id: "rules",
    number: FIRST_ADVANCED_STEP_NUMBER + 2,
    name: "Rules",
    header: "What happens when…?",
    helper:
      "Rules react to your tracked values: they guide the narrator, change values, or both.",
  },
  {
    id: "hard_limits",
    number: FIRST_ADVANCED_STEP_NUMBER + 3,
    name: "Hard limits",
    header: "What can never happen?",
    helper:
      "Hard limits block any change that breaks them. Lowest and highest already protect a single value — use hard limits when one value depends on another, or when something must never happen in a certain situation.",
  },
  {
    id: "extras",
    number: FIRST_ADVANCED_STEP_NUMBER + 4,
    name: "Extras",
    header: "Want to add more?",
    helper: "All optional. Add any, anytime.",
  },
];
