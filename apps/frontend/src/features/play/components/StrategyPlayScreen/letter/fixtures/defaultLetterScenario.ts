import type { StrategyLetterPackage } from "../../../../types/letterScene.types";

export const DEFAULT_LETTER_SCENARIO: StrategyLetterPackage = {
  sceneId: "scene-letter-dunmere-mira-08",
  dispatchId: "POUCH-D-4",
  dispatchNumber: 8,
  provenance: {
    senderName: "Queen Mira",
    senderTitle: "Sovereign of the Dun",
    senderKeep: "Dunmere Keep",
    portraitUrl: "",
    temperament: "Courteous • Guarded Kin",
    temperamentIcon: "peaceful",
    outriderLog: "Arrived by swift outrider from Dunmere Keep at dawn.",
    distanceLeagues: 18,
    historicTieNote:
      "We held the ford together at harvest three springs ago. Blood runs thicker than seasonal tax.",
  },
  incoming: {
    dispatchNumber: 8,
    locationHeader: "Dunmere Solar • Feast of St. Jude",
    dateSolar: "Late Autumn, Eleventh Year",
    salutation: "To my brother Aldric, ruler of the Marches,",
    paragraphs: [
      "The early frost has touched our northern orchards, yet the warmth of our concord remains steadfast. We hear through the peddlers that your valley harvest in Greenford Shire has filled every tithe barn to overflowing.",
      "Our border garrisons along the River Dun report uneasy murmurs among the highland sheep-reeves. Two boundary stones near Ashford Ford were moved in the night mist; a petty slight, surely born of restless bailiffs rather than royal decree.",
      "Send two grain barges downriver before the river freeze, brother. Let our bailiffs survey the boundary together beneath a shared banner, that winter find us with full bellies and dry swords.",
    ],
    signoffPlace: "Written in our solar at High Dunmere, upon the feast of Saint Jude,",
    signoffSignature: "Mira, Regina",
    isSealIntactPriorToDawn: true,
  },
  scribe: {
    name: "Brother Lucan",
    title: "Royal Scribe",
    avatarUrl: "",
  },
  initialDraft: {
    revisionIndex: 1,
    instruction: "Tell her I can spare grain, but not before the harvest, and I want the border left alone.",
    salutation: "To Queen Mira, honored sister and sovereign of Dunmere,",
    paragraphs: [
      "We received your outrider with the morning bell, and we share your wish that winter find both our realms with full hearths and untroubled borders.",
      "We can spare eighty cartloads of Greenford grain downriver once our own winter stores are locked beneath the granary beam, but not before the late harvest is gathered in full.",
      "Concerning the boundary stones at Ashford Ford: our bailiffs shall walk the line in spring alongside yours. Until then, let neither horse nor stone be stirred across the river gravel, that peace may rest unbroken.",
    ],
    signoffText: "Written in our solar at High Cairn,",
    authorTitle: "Lord Marshal of the Marches",
  },
};
