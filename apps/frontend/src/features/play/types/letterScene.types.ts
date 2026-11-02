export type LetterStage = "reading" | "drafting";
export type DocketChoice = "write" | "scribe" | "aside" | "decline";

export interface LetterProvenance {
  senderName: string;
  senderTitle: string;
  senderKeep: string;
  portraitUrl: string;
  temperament: string;
  temperamentIcon: string;
  outriderLog: string;
  distanceLeagues: number;
  historicTieNote: string;
}

export interface IncomingLetterContent {
  dispatchNumber: number;
  locationHeader: string;
  dateSolar: string;
  salutation: string;
  paragraphs: string[];
  signoffPlace: string;
  signoffSignature: string;
  isSealIntactPriorToDawn: boolean;
}

export interface ScribeProfile {
  name: string;
  title: string;
  avatarUrl: string;
}

export interface DraftRevision {
  revisionIndex: number;
  instruction: string;
  salutation: string;
  paragraphs: string[];
  signoffText: string;
  authorTitle: string;
}

export interface StrategyLetterPackage {
  sceneId: string;
  dispatchId: string;
  dispatchNumber: number;
  provenance: LetterProvenance;
  incoming: IncomingLetterContent;
  scribe: ScribeProfile;
  initialDraft: DraftRevision;
  isDeclinable?: boolean;
}

export interface LetterSealSubmission {
  sceneId: string;
  finalProse: string;
  instructionSummary?: string;
  revisionCount: number;
}

export type ScribeDraftRequester = (
  instruction: string,
  currentProse: string,
) => Promise<string>;

export type LetterSealHandler = (
  submission: LetterSealSubmission,
) => void | boolean | Promise<boolean | void>;
