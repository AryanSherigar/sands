import type { BarListItem, ChartDatum, ChartTone } from "../../types/statsView.types";

export interface SeriesChartProps {
  data: ChartDatum[];
  ariaLabel: string;
  tone: ChartTone;
}

export interface BarListProps {
  items: BarListItem[];
  ariaLabel: string;
  tone: ChartTone;
}

export interface BarListRowProps {
  item: BarListItem;
  top: number;
  tone: ChartTone;
}
