import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { toChartTable } from "../../lib/chartData";
import { formatCount, formatDecimal } from "../../lib/statsFormat";
import { ChartFigure } from "./ChartFigure";
import { Histogram } from "./Histogram";
import { ReviewList } from "./ReviewList";
import { StatTile } from "./StatTile";
import { StatsSection } from "./StatsSection";
import type { ReviewsPanelProps } from "./panels.types";

export const ReviewsPanel: React.FC<ReviewsPanelProps> = ({
  reviews,
  isSampleSufficient,
}) => {
  const data = reviews.histogram.map((bucket) => ({
    label: `${bucket.rating}★`,
    value: bucket.count,
  }));
  const summary = `${formatCount(reviews.review_count)} reviews averaging ${formatDecimal(reviews.average_rating)} stars.`;
  const shares = `${formatCount(reviews.share_counts.spectate)} · ${formatCount(reviews.share_counts.join)}`;
  return (
    <StatsSection section={STATS_SECTIONS.reviews}>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Avg rating" value={formatDecimal(reviews.average_rating)} />
        <StatTile label="Reviews" value={formatCount(reviews.review_count)} />
        <StatTile label="Bookmarks" value={formatCount(reviews.bookmark_count)} />
        <StatTile label="Share links (spectate · join)" value={shares} />
      </div>
      {isSampleSufficient && reviews.review_count > 0 && (
        <ChartFigure
          title="Rating distribution"
          summary={summary}
          table={toChartTable(data, "Rating", "Reviews")}
        >
          <Histogram data={data} ariaLabel={summary} tone="accent" />
        </ChartFigure>
      )}
      <ReviewList reviews={reviews.latest} showScenario={false} />
    </StatsSection>
  );
};
