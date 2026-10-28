import React from "react";
import type { GuideStepId } from "../../../constants/guideSteps";
import { useGoToGuideStep } from "../../../hooks/useGoToGuideStep";
import { useUsedIn } from "../../../hooks/useUsedIn";
import { useValueOptions } from "../../../hooks/useValueOptions";
import { countMisfitPlaces } from "../../../lib/comparisonFit";
import { formatMisfitNote } from "../../../constants/trackedValues";
import type { UsedInListProps } from "./Advanced.types";

const UNTITLED_ENDING = "Untitled ending";
const UNTITLED_RULE = "Untitled rule";
const UNTITLED_LIMIT = "Untitled hard limit";
const UNTITLED_LINK = "a link between cards";

const USED_IN_CHIP_CLASS =
  "rounded-sm border border-border-strong bg-surface-inset px-2.5 py-1 text-micro text-content-muted";

interface UsedInItem {
  id: string;
  text: string;
  stepId: GuideStepId | null;
}

export const UsedInList: React.FC<UsedInListProps> = ({ valueKey }) => {
  const usedIn = useUsedIn(valueKey);
  const option = useValueOptions().find((candidate) => candidate.path === valueKey);
  const misfitCount = option ? countMisfitPlaces(option, usedIn) : 0;
  const goToStep = useGoToGuideStep();
  const items: UsedInItem[] = [
    ...usedIn.endings.map((ending) => ({
      id: ending.end_condition_id,
      text: `Ending: ${ending.outcome_title.trim() || UNTITLED_ENDING}`,
      stepId: "endings" as const,
    })),
    ...usedIn.rules.map((rule) => ({
      id: rule.condition_id,
      text: `Rule: ${rule.label.trim() || UNTITLED_RULE}`,
      stepId: "rules" as const,
    })),
    ...usedIn.limits.map((limit) => ({
      id: limit.invariant_id,
      text: `Hard limit: ${limit.label.trim() || UNTITLED_LIMIT}`,
      stepId: "hard_limits" as const,
    })),
    ...usedIn.links.map((link) => ({
      id: link.fact_id,
      text: `Link: ${link.predicate.trim() || UNTITLED_LINK}`,
      stepId: null,
    })),
  ];

  return (
    <div role="group" aria-label="Used in" className="space-y-1.5">
      <p className="text-meta font-medium text-content-muted">Used in</p>
      {items.length === 0 && <p className="text-micro text-content-faint">Not used yet.</p>}
      <ul className="flex flex-wrap gap-2">
        {items.map(({ id, text, stepId }) => (
          <li key={id}>
            {stepId === null ? (
              <span className={`${USED_IN_CHIP_CLASS} inline-block`}>{text}</span>
            ) : (
              <button
                type="button"
                onClick={() => goToStep(stepId)}
                className={`${USED_IN_CHIP_CLASS} transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary`}
              >
                {text}
              </button>
            )}
          </li>
        ))}
      </ul>
      {misfitCount > 0 && (
        <p className="text-meta text-danger">
          {formatMisfitNote(option?.label ?? valueKey, misfitCount)}
        </p>
      )}
    </div>
  );
};
