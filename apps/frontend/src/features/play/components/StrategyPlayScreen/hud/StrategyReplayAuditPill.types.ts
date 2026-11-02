import type { ReplayVerificationResponse } from "../../../api/simulation.api";

export interface StrategyReplayAuditPillProps {
  playthroughId?: string;
  throughTurn?: number;
  onVerified?: (result: ReplayVerificationResponse) => void;
}
