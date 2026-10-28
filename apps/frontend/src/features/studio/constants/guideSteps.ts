export type GuideStepId =
  | "idea"
  | "premise"
  | "player"
  | "characters"
  | "world"
  | "opening"
  | "endings"
  | "tracked_values"
  | "rules"
  | "hard_limits"
  | "extras"
  | "finish";

export interface GuideStepDefinition {
  id: GuideStepId;
  number: number;
  name: string;
  header: string;
  helper: string | null;
}

export const BASE_GUIDE_STEPS: readonly GuideStepDefinition[] = [
  {
    id: "idea",
    number: 1,
    name: "Idea",
    header: "What's your story in one sentence?",
    helper: "Start small. You can change anything later.",
  },
  {
    id: "premise",
    number: 2,
    name: "Premise",
    header: "Tell us about your story, the stakes.",
    helper: null,
  },
  {
    id: "player",
    number: 3,
    name: "Player",
    header: "Who will the player be?",
    helper: null,
  },
  {
    id: "characters",
    number: 4,
    name: "Characters",
    header: "Who will the player meet?",
    helper: "Two or three is plenty. You can add more anytime.",
  },
  {
    id: "world",
    number: 5,
    name: "World",
    header: "Tell us about your world.",
    helper:
      "Write as much as you like. The narrator recalls the parts that matter in each scene.",
  },
  {
    id: "opening",
    number: 6,
    name: "Opening",
    header: "Where does the story begin?",
    helper:
      "Describe the moment the story starts. The narrator writes the first scene from this.",
  },
  {
    id: "finish",
    number: 7,
    name: "Finish",
    header: "Ready to share your story?",
    helper: null,
  },
];
