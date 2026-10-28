import type { EconomyLedgerLine } from "../../../types/turnReport.types";

export interface EconomyLedgerCardProps {
  lines: EconomyLedgerLine[];
  netGold: number;
}
