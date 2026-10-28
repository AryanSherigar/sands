import type { ReactNode } from "react";

export interface StatChipProps {
  icon: ReactNode;
  value: string;
  trend?: string;
  tooltipTitle: string;
  tooltipDesc: string;
}
