import type { ContinueRun } from "../../../types/overview.types";

export interface ContinueRunCardProps {
  run: ContinueRun;
  isPrimary: boolean;
  now: Date;
}
