import { STATS_SECTIONS } from "../constants/stats";
import type { ScenarioStatsResponse } from "../types/stats.types";
import type { StatsSectionLink } from "../types/statsView.types";

export const visibleStatsSections = (stats: ScenarioStatsResponse): StatsSectionLink[] => {
  const sections: StatsSectionLink[] = [STATS_SECTIONS.plays];
  if (stats.outcomes !== null) sections.push(STATS_SECTIONS.outcomes);
  sections.push(STATS_SECTIONS.engagement, STATS_SECTIONS.funnel, STATS_SECTIONS.reviews);
  if (stats.versions.length > 0) sections.push(STATS_SECTIONS.versions);
  if (stats.benchmarks !== null) sections.push(STATS_SECTIONS.benchmarks);
  if (stats.is_sample_sufficient && stats.heatmap.length > 0) {
    sections.push(STATS_SECTIONS.heatmap);
  }
  return sections;
};
