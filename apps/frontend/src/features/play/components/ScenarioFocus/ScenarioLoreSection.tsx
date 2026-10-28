import React, { useRef, useState } from "react";
import { IconChevronDown } from "@tabler/icons-react";
import { LORE_COLLAPSED_LINES_CLASS } from "../../constants/scenarioPage.constants";
import { useIsClamped } from "../../hooks/useIsClamped";
import type { ScenarioDetailResponse } from "../../types/scenario";
import { SectionHeading } from "./SectionHeading";

interface ScenarioLoreSectionProps {
  scenario: ScenarioDetailResponse;
}

const extractLoreText = (
  worldData: Record<string, unknown>,
  defaultLogline?: string | null,
): string => {
  if (typeof worldData.lore === "string") return worldData.lore;
  if (typeof worldData.description === "string") return worldData.description;
  return defaultLogline || "";
};

export const ScenarioLoreSection: React.FC<ScenarioLoreSectionProps> = ({
  scenario,
}) => {
  const loreRef = useRef<HTMLParagraphElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const worldData = (scenario.world_data || {}) as Record<string, unknown>;
  const loreText = extractLoreText(worldData, scenario.logline);
  const isClamped = useIsClamped(loreRef, loreText);
  const hasLore = Boolean(loreText) && loreText !== scenario.logline;

  return (
    <section aria-labelledby="scenario-about-heading">
      <SectionHeading id="scenario-about-heading" label="About" />

      {scenario.logline && (
        <p className="font-display text-xl leading-relaxed text-content md:text-2xl">
          {scenario.logline}
        </p>
      )}

      {hasLore && (
        <p
          ref={loreRef}
          className={`mt-4 whitespace-pre-line font-sans text-[15px] leading-relaxed text-content-muted ${
            isExpanded ? "" : LORE_COLLAPSED_LINES_CLASS
          }`}
        >
          {loreText}
        </p>
      )}

      {hasLore && (isClamped || isExpanded) && (
        <button
          type="button"
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded((current) => !current)}
          className="mt-2 inline-flex items-center gap-1 font-sans text-sm font-medium text-accent hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          {isExpanded ? "Show less" : "Read more"}
          <IconChevronDown
            size={16}
            aria-hidden="true"
            className={isExpanded ? "rotate-180" : ""}
          />
        </button>
      )}

      {!scenario.logline && !hasLore && (
        <p className="font-sans text-sm text-content-faint">
          No backstory recorded yet — start a playthrough to uncover it.
        </p>
      )}
    </section>
  );
};
