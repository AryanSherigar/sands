import React from "react";
import { Link } from "react-router-dom";
import type { InProgressLineProps } from "./InProgressLine.types";

const LINK_CLASSES =
  "font-semibold text-accent underline-offset-4 hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent";

export const InProgressLine: React.FC<InProgressLineProps> = ({
  scenarioId,
  summary,
}) => {
  if (summary.kind === "none") return null;

  if (summary.kind === "multiple") {
    return (
      <p className="font-sans text-sm text-content-muted">
        You have {summary.count} runs in progress ·{" "}
        <Link
          to={`/profile?tab=campaigns&scenario=${scenarioId}`}
          className={LINK_CLASSES}
        >
          View
        </Link>
      </p>
    );
  }

  return (
    <p className="font-sans text-sm text-content-muted">
      You have a run in progress · Turn {summary.turnCount} —{" "}
      <Link to={`/play/${summary.playthroughId}`} className={LINK_CLASSES}>
        Continue
      </Link>
    </p>
  );
};
