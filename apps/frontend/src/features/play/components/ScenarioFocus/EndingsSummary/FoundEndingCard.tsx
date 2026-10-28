import React from "react";
import { IconSkull, IconTrophy } from "@tabler/icons-react";
import { OUTCOME_LABELS } from "../../../constants/scenarioPage.constants";
import { formatEndingDate } from "../../../utils/scenarioPage.utils";
import type { FoundEndingCardProps } from "./FoundEndingCard.types";

export const FoundEndingCard: React.FC<FoundEndingCardProps> = ({ ending }) => {
  const OutcomeIcon = ending.outcome_tag === "lose" ? IconSkull : IconTrophy;

  return (
    <li className="space-y-2 rounded-md border border-border-subtle bg-surface-raised p-4">
      <div className="flex items-center justify-between gap-2 font-mono text-xs uppercase tracking-wide text-accent">
        <span>
          Turn {ending.turn_reached}
          {ending.outcome_tag ? ` · ${OUTCOME_LABELS[ending.outcome_tag]}` : ""}
        </span>
        <OutcomeIcon size={16} stroke={1.5} aria-hidden="true" />
      </div>
      <h3 className="font-display text-sm font-bold text-content">
        {ending.title}
      </h3>
      {ending.text && (
        <p className="font-sans text-xs leading-relaxed text-content-muted">
          {ending.text}
        </p>
      )}
      <p className="font-mono text-[11px] text-content-faint">
        Found {formatEndingDate(ending.found_at)}
      </p>
    </li>
  );
};
