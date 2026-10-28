import type { CardKind } from "./card.types";

interface PickQuestionTarget {
  kind: CardKind | "any";
  predicate: string;
}

export interface GuideQuestion {
  id: string;
  label: string;
  prompt: string;
  pick?: PickQuestionTarget;
}

export interface QuestionGroup {
  id: string;
  name: string;
  questions: GuideQuestion[];
}

export interface PickOption {
  id: string;
  name: string;
  kind: CardKind;
}
