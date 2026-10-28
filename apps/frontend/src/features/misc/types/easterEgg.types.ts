export type FactCategory = "anime" | "song";

export interface EasterEggFact {
  id: string;
  category: FactCategory;
  title: string;
  fact: string;
  tags: string[];
}

type TerminalLineType =
  | "system"
  | "input"
  | "fact"
  | "list"
  | "help"
  | "error";

export interface TerminalLine {
  id: string;
  type: TerminalLineType;
  content: string;
  fact?: EasterEggFact;
}
