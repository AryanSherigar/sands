import React from "react";
import { IconCalendar } from "@tabler/icons-react";
import { WEEKDAY_INITIALS } from "../../../constants/overview.constants";
import {
  formatPlayedDaysText,
  formatWeeklyCaption,
} from "../../../lib/weeklyActivity";
import type { WeeklyActivityDotsProps } from "./WeeklyActivityDots.types";

export const WeeklyActivityDots: React.FC<WeeklyActivityDotsProps> = ({
  activity,
}) => (
  <section
    aria-labelledby="weekly-rhythm-heading"
    className="flex flex-col justify-between gap-4 rounded-md border border-border-subtle bg-surface-raised p-4 sm:flex-row sm:items-center"
  >
    <div className="space-y-1">
      <h2
        id="weekly-rhythm-heading"
        className="flex items-center gap-2 font-display text-lg font-semibold text-content"
      >
        <IconCalendar size={20} stroke={1.5} aria-hidden="true" />
        Weekly Rhythm
      </h2>
      <p className="text-sm text-content-muted">
        {formatWeeklyCaption(activity.played_day_count)}
      </p>
      <p className="sr-only">{formatPlayedDaysText(activity.played_days)}</p>
    </div>
    <ol
      aria-hidden="true"
      className="flex gap-3 rounded-md border border-border-subtle bg-surface-inset px-3 py-2"
    >
      {WEEKDAY_INITIALS.map((initial, index) => (
        <li key={index} className="flex flex-col items-center gap-1.5">
          <span className="font-mono text-xs text-content-faint">{initial}</span>
          <span
            data-testid="weekly-dot"
            className={`h-2.5 w-2.5 rounded-full ${
              activity.played_days[index] ? "bg-content" : "bg-border-strong"
            }`}
          />
        </li>
      ))}
    </ol>
  </section>
);
