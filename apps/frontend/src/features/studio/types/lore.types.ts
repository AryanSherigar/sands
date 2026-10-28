type LoreBlockKind = "text" | "answer";

export interface LoreBlock {
  kind: LoreBlockKind;
  question_id?: string | null;
  label?: string | null;
  text: string;
}

export interface LoreDocument {
  blocks: LoreBlock[];
}
