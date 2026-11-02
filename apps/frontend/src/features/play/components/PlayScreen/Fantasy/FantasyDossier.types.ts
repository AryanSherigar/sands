import type { ReactNode } from "react";
import type { PlaythroughData } from "../../../types/play.types";

export interface FantasyDossierProps {
  playthrough: PlaythroughData;
  canTalk?: boolean;
  map?: ReactNode;
  mapRequest?: number;
  onClose: () => void;
  onTalk: (characterName: string) => void;
  onOpenCodex: () => void;
}

export type DossierTab = "party" | "quests" | "relics" | "map";
