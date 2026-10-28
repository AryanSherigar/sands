import React from "react";
import {
  formatEndingsCompletion,
  formatGenresSubtext,
} from "../../../lib/overviewFormat";
import type { LifetimeStatsProps } from "./LifetimeStats.types";

export const LifetimeStats: React.FC<LifetimeStatsProps> = ({ stats }) => {
  const tiles = [
    {
      label: "Turns Taken",
      value: stats.turns_taken,
      subtext: `Across ${stats.campaigns_count} campaigns`,
    },
    {
      label: "Stories Completed",
      value: stats.stories_completed,
      subtext: "Concluded narratives",
    },
    {
      label: "Endings Found",
      value: stats.endings_found,
      total: stats.endings_total,
      subtext: formatEndingsCompletion(
        stats.endings_found,
        stats.endings_total,
      ),
    },
    {
      label: "Worlds Played",
      value: stats.worlds_played,
      subtext: "Unique scenarios",
    },
    {
      label: "Genres Explored",
      value: stats.genres_explored.length,
      subtext: formatGenresSubtext(stats.genres_explored),
    },
  ];

  return (
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="rounded-md border border-border-subtle bg-surface-raised p-4"
        >
          <dt className="text-xs text-content-muted">{tile.label}</dt>
          <dd className="mt-1 font-mono text-2xl font-semibold text-content">
            {tile.value.toLocaleString()}
            {tile.total ? (
              <span className="ml-1 text-base font-normal text-content-faint">
                / {tile.total.toLocaleString()}
              </span>
            ) : null}
          </dd>
          <dd className="mt-1 truncate text-xs text-content-faint">
            {tile.subtext}
          </dd>
        </div>
      ))}
    </dl>
  );
};
