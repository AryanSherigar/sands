import type React from "react";
import type { StatsTableData } from "../../types/statsView.types";

export interface ChartFigureProps {
  title: string;
  summary: string;
  table: StatsTableData;
  children: React.ReactNode;
}
