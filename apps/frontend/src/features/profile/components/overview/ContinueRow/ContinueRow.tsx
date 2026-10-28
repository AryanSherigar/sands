import React from "react";
import { IconPlayerPlay } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { TabEmptyState } from "../../states/TabEmptyState";
import { ContinueRunCard } from "../ContinueRunCard/ContinueRunCard";
import type { ContinueRowProps } from "./ContinueRow.types";

const EXPLORE_ACTION = { label: "Explore stories", to: "/discover" };

export const ContinueRow: React.FC<ContinueRowProps> = ({ runs, now }) => (
  <section aria-labelledby="continue-heading" className="space-y-4">
    <div className="flex items-center justify-between gap-3">
      <h2
        id="continue-heading"
        className="flex items-center gap-2 font-display text-xl font-semibold text-content"
      >
        <IconPlayerPlay size={20} stroke={1.5} aria-hidden="true" />
        Continue Your Narrative
      </h2>
      {runs.length > 0 && (
        <Link
          to="/profile?tab=campaigns"
          className="text-sm text-content-muted hover:text-content hover:underline"
        >
          All active runs
        </Link>
      )}
    </div>
    {runs.length === 0 ? (
      <TabEmptyState message="No active runs" action={EXPLORE_ACTION} />
    ) : (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {runs.map((run, index) => (
          <ContinueRunCard
            key={run.playthrough_id}
            run={run}
            isPrimary={index === 0}
            now={now}
          />
        ))}
      </div>
    )}
  </section>
);
