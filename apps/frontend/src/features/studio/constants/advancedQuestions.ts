import type { QuestionGroup } from "../types/guide.types";

export const ENDING_QUESTION_GROUPS: QuestionGroup[] = [
  {
    id: "ending",
    name: "The ending",
    questions: [
      { id: "ending-last-moment", label: "The last moment", prompt: "What does the player see in the last moment?" },
      { id: "ending-characters", label: "The characters", prompt: "What happens to the characters?" },
      { id: "ending-world-after", label: "The world after", prompt: "What does the world look like after?" },
      { id: "ending-last-line", label: "The last line", prompt: "What's the last line?" },
    ],
  },
];
