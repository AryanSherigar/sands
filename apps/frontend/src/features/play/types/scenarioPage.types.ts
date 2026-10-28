export interface AgeChip {
  label: string;
  explanation: string;
  isMature: boolean;
}

export type InProgressSummary =
  | { kind: "none" }
  | { kind: "single"; playthroughId: string; turnCount: number }
  | { kind: "multiple"; count: number };

export interface SetupSummary {
  requiredLabels: string[];
  optionalCount: number;
  isQuickStart: boolean;
}

export interface RatingBucket {
  stars: number;
  count: number;
  percent: number;
}
