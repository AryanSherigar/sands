import type {
  DraftRevision,
  StrategyLetterPackage,
} from "../types/letterScene.types";
import type { SceneViewResponse } from "../types/scene.types";
import { splitProse } from "./letter-prose";

const UNKNOWN_SENDER = "A rival ruler";
const SENDER_TITLE = "Sovereign";
const SCRIBE_NAME = "Your scribe";
const SCRIBE_TITLE = "Court scribe";
const TOPIC_FACT_LABEL = "Topic";
const FALLBACK_TOPIC = "courtesy";
const MAIL_ICON = "mail";

const readTopic = (view: SceneViewResponse): string => {
  const fact = view.situation.facts.find((item) => item.label === TOPIC_FACT_LABEL);
  return (fact?.value ?? FALLBACK_TOPIC).replace(/_/g, " ");
};

const emptyDraft = (): DraftRevision => ({
  revisionIndex: 1,
  instruction: "",
  salutation: "",
  paragraphs: [""],
  signoffText: "",
  authorTitle: "",
});

export const buildLetterPackage = (
  view: SceneViewResponse,
  incomingText: string,
): StrategyLetterPackage => ({
  sceneId: view.scene_id,
  dispatchId: view.scene_id,
  dispatchNumber: view.turn,
  provenance: {
    senderName: view.participants[0]?.name ?? UNKNOWN_SENDER,
    senderTitle: SENDER_TITLE,
    senderKeep: "",
    portraitUrl: "",
    temperament: `A letter of ${readTopic(view)}`,
    temperamentIcon: MAIL_ICON,
    outriderLog: "",
    distanceLeagues: 0,
    historicTieNote: "",
  },
  incoming: {
    dispatchNumber: view.turn,
    locationHeader: "",
    dateSolar: `Turn ${view.turn}`,
    salutation: "",
    paragraphs: splitProse(incomingText),
    signoffPlace: "",
    signoffSignature: "",
    isSealIntactPriorToDawn: false,
  },
  scribe: { name: SCRIBE_NAME, title: SCRIBE_TITLE, avatarUrl: "" },
  initialDraft: emptyDraft(),
  isDeclinable: view.is_declinable ?? true,
});
