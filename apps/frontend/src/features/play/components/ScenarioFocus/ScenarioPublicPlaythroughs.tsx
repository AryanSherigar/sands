import React from "react";
import { PublicPlaythroughSummary } from "../../types/scenario";
import { SectionError } from "./SectionError/SectionError";
import { SectionHeading } from "./SectionHeading";

interface ScenarioPublicPlaythroughsProps {
  playthroughs: PublicPlaythroughSummary[];
  isError: boolean;
  onRetry: () => void;
}

const EMPTY_COPY = "No public playthroughs yet";

export const ScenarioPublicPlaythroughs: React.FC<
  ScenarioPublicPlaythroughsProps
> = ({ playthroughs, isError, onRetry }) => {
  return (
    <section
      aria-labelledby="scenario-playthroughs-heading"
      className="rounded-md border border-border-subtle bg-surface-raised p-5"
    >
      <SectionHeading
        id="scenario-playthroughs-heading"
        label="Public playthroughs"
        trailing={
          <span className="font-mono text-xs text-content-faint">
            {playthroughs.length} public
          </span>
        }
      />

      {isError && <SectionError label="playthroughs" onRetry={onRetry} />}

      {!isError && playthroughs.length === 0 && (
        <p className="font-sans text-sm text-content-faint">{EMPTY_COPY}</p>
      )}

      {!isError && playthroughs.length > 0 && (
        <ul className="divide-y divide-border-subtle">
          {playthroughs.map((pt) => (
            <li
              key={pt.playthrough_id}
              className="flex items-center justify-between gap-3 py-3 first:pt-0"
            >
              <div className="min-w-0">
                <p className="truncate font-sans text-sm text-content">
                  {pt.character_name || "Unknown adventurer"}
                </p>
                <p className="truncate font-mono text-xs text-content-faint">
                  {pt.player_name} · turn {pt.turn_count}
                </p>
              </div>
              <span
                className={`flex shrink-0 items-center gap-1.5 font-mono text-xs capitalize ${
                  pt.status === "completed" ? "text-success" : "text-accent"
                }`}
              >
                <span
                  aria-hidden="true"
                  className="h-1.5 w-1.5 rounded-full bg-current"
                />
                {pt.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
