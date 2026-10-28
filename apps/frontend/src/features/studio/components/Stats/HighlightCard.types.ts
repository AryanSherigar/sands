import type { OverviewHighlight } from "../../types/stats.types";

export interface HighlightCardProps {
  heading: string;
  highlight: OverviewHighlight | null;
  formatValue: (value: number) => string;
}
