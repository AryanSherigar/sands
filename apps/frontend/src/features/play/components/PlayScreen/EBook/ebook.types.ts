import {
  ChapterDelta,
  MasterEntity,
  Objective,
  PlayerStat,
  TurnLogItem,
} from "../../../types/play.types";

export interface EBookHeaderProps {
  onBack: () => void;
  onOpenCodex: () => void;
  onOpenChronicle: () => void;
}

export interface ChapterSummaryStripProps {
  delta: ChapterDelta;
}

export type CharacterDrawerTab =
  "stats" | "inventory" | "factions" | "objectives";

export interface CharacterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  playerStats: PlayerStat[];
  playerInventory: MasterEntity[];
  entities: MasterEntity[];
  objectives: Objective[];
}

export interface EBookPrologueCardProps {
  premise: string;
  onStartAction: () => void;
}

export interface EBookTurnEntryProps {
  turn: TurnLogItem;
  turnIndex: number;
  isLatest: boolean;
  shouldDistort?: boolean;
}

export interface EBookBottomBarProps {
  isSpectator: boolean;
  // Multiplayer turn-order gate. Defaults to true (newbie/solo never gate).
  canAct?: boolean;
  // Display name of whoever acts next, shown when canAct is false.
  waitingOnLabel?: string | null;
  // Master mode only — true once an end condition has matched. Blocks
  // further action submission the same way isSpectator does.
  isEnded?: boolean;
  hasRulesPanel?: boolean;
}

export interface EBookActionDrawerProps {
  onSubmit: (actionText: string) => void;
  onContinue: () => void;
  onRetry: () => void;
  // True only after an error or interruption; hidden once a turn has saved,
  // because a retry then would spend quota on a new turn with the same text.
  canRetry: boolean;
  isNarrating: boolean;
  // Lets voice transcription bias toward this playthrough's entity names.
  playthroughId?: string;
  // Master mode only — omitted (or empty) renders no chip row.
  actionChips?: string[];
}

export interface ChronicleRecapModalProps {
  isOpen: boolean;
  onClose: () => void;
}
