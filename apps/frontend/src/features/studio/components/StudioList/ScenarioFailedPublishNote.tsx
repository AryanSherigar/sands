import React from "react";
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import { STUDIO_REVIEW_STEP_HASH } from "../../constants/studio-list";
import type { ScenarioFailedPublishNoteProps } from "./StudioList.types";

export const ScenarioFailedPublishNote: React.FC<
  ScenarioFailedPublishNoteProps
> = ({ scenario }) => (
  <div className="flex flex-col gap-1">
    <p
      className="truncate font-mono text-xs text-danger"
      title={scenario.publish_error ?? undefined}
    >
      {scenario.publish_error}
    </p>
    <Link
      to={`/studio/${scenario.scenario_id}/edit${STUDIO_REVIEW_STEP_HASH}`}
      className="inline-flex items-center gap-1 font-mono text-xs text-danger hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      Fix and republish
      <IconArrowRight size={14} aria-hidden="true" />
    </Link>
  </div>
);
