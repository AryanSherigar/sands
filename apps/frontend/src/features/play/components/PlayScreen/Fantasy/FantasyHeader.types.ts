import type { RefObject } from "react";

export interface FantasyHeaderProps {
  scenarioTitle: string;
  folioTitle: string;
  turnNumber: number;
  isNarrating: boolean;
  isDossierOpen: boolean;
  dossierButton: RefObject<HTMLButtonElement>;
  onBack: () => void;
  onOpenCodex: () => void;
  onOpenChronicle: () => void;
  onOpenMap?: () => void;
  onToggleDossier: () => void;
}
