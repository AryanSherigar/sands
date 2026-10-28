import type { GuideQuestion, PickOption, QuestionGroup } from "../../types/guide.types";
import type { LoreBlock, LoreDocument } from "../../types/lore.types";

export interface LoreBoxProps {
  document: LoreDocument;
  onChange: (next: LoreDocument) => void;
  softWordGuide?: string;
  questions?: QuestionGroup[];
  ariaLabel?: string;
  placeholder?: string;
  pickOptions?: PickOption[];
  onPick?: (question: GuideQuestion, option: PickOption) => void;
  onRemovePick?: (question: GuideQuestion, pickedName: string) => void;
  onAddToAlwaysRemember?: (line: string) => void;
}

export interface LinkedBlockProps {
  block: LoreBlock;
  index: number;
  canMoveUp: boolean;
  canMoveDown: boolean;
  isPicked: boolean;
  isMissing: boolean;
  onEdit: (index: number, text: string) => void;
  onRemove: (index: number) => void;
  onUnlink: (index: number) => void;
  onMove: (index: number, offset: number) => void;
  onAddToAlwaysRemember?: (line: string) => void;
}

export interface QuestionFieldProps {
  question: GuideQuestion;
  document: LoreDocument;
  pickOptions: PickOption[];
  onAnswer: (question: GuideQuestion, text: string) => void;
  onPick: (question: GuideQuestion, option: PickOption) => void;
}

export interface QuestionsToHelpProps {
  groups: QuestionGroup[];
  document: LoreDocument;
  pickOptions: PickOption[];
  onAnswer: (question: GuideQuestion, text: string) => void;
  onPick: (question: GuideQuestion, option: PickOption) => void;
}

export interface QuestionGroupSectionProps extends QuestionsToHelpGroupContext {
  group: QuestionGroup;
  isOpen: boolean;
  onToggle: () => void;
}

interface QuestionsToHelpGroupContext {
  document: LoreDocument;
  pickOptions: PickOption[];
  onAnswer: (question: GuideQuestion, text: string) => void;
  onPick: (question: GuideQuestion, option: PickOption) => void;
}
