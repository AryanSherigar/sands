import React from "react";
import { IconAward } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { RecentMilestonesProps } from "./RecentMilestones.types";

const formatEarnedDate = (earnedAt: string): string =>
  new Date(earnedAt).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });

export const RecentMilestones: React.FC<RecentMilestonesProps> = ({
  milestones,
}) => (
  <section
    aria-labelledby="milestones-heading"
    className="space-y-4 rounded-md border border-border-subtle bg-surface-raised p-4"
  >
    <div className="flex items-center justify-between gap-3">
      <h2
        id="milestones-heading"
        className="flex items-center gap-2 font-display text-lg font-semibold text-content"
      >
        <IconAward size={20} stroke={1.5} aria-hidden="true" />
        Recent Milestones
      </h2>
      {milestones.length > 0 && (
        <Link
          to="/profile?tab=achievements"
          className="text-sm text-content-muted hover:text-content hover:underline"
        >
          View all achievements
        </Link>
      )}
    </div>
    {milestones.length === 0 ? (
      <p className="text-sm text-content-muted">No milestones yet</p>
    ) : (
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {milestones.map((milestone) => (
          <li
            key={milestone.key}
            className="rounded-md border border-border-subtle bg-surface-inset p-3"
          >
            <p className="text-sm font-medium text-content">{milestone.name}</p>
            <p className="mt-1 font-mono text-xs text-content-faint">
              Earned {formatEarnedDate(milestone.earned_at)}
            </p>
          </li>
        ))}
      </ul>
    )}
  </section>
);
