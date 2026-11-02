import type {
  StrategyLetterPackage,
  LetterProvenance,
  IncomingLetterContent,
  DocketChoice,
} from "../../../../types/letterScene.types";

export interface LetterPouchStageProps {
  pkg: StrategyLetterPackage;
  onSelectDocket: (choice: DocketChoice) => void;
}

export interface LetterProvenanceFlapProps {
  provenance: LetterProvenance;
  dispatchId: string;
}

export interface LetterManuscriptSheetProps {
  incoming: IncomingLetterContent;
  portraitUrl: string;
}

export interface LetterReplyDocketsFlapProps {
  senderName: string;
  isDeclinable: boolean;
  onSelect: (choice: DocketChoice) => void;
}
