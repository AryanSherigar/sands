import React from "react";
import { IconAlertTriangle, IconShieldCheck } from "@tabler/icons-react";
import {
  getAgeChip,
  getMechanicalChips,
  getThematicChips,
} from "../../../utils/scenarioPage.utils";
import { SectionHeading } from "../SectionHeading";
import type { ContentTagListProps } from "./ContentTagList.types";

const CHIP_CLASSES =
  "flex cursor-help items-center gap-1.5 rounded-sm border border-border-subtle bg-surface-raised px-3 py-1.5 font-sans text-xs font-medium text-content hover:border-border-strong focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent";

export const ContentTagList: React.FC<ContentTagListProps> = ({ scenario }) => {
  const chips = [...getThematicChips(scenario), ...getMechanicalChips(scenario)];
  const ageChip = getAgeChip(scenario);
  if (chips.length === 0 && !ageChip) return null;

  return (
    <section aria-labelledby="scenario-tags-heading">
      <SectionHeading
        id="scenario-tags-heading"
        label="Mechanical & thematic profile"
      />
      <ul className="flex flex-wrap gap-2">
        {chips.map(({ id, label, explanation, Icon }) => (
          <li key={id} tabIndex={0} title={explanation} className={CHIP_CLASSES}>
            <Icon size={15} stroke={1.5} className="text-accent" aria-hidden="true" />
            {label}
            <span className="sr-only">. {explanation}</span>
          </li>
        ))}
        {ageChip && (
          <li
            tabIndex={0}
            title={ageChip.explanation}
            className={CHIP_CLASSES}
          >
            {ageChip.isMature ? (
              <IconAlertTriangle
                size={15}
                stroke={1.5}
                className="text-danger"
                aria-hidden="true"
              />
            ) : (
              <IconShieldCheck
                size={15}
                stroke={1.5}
                className="text-content-muted"
                aria-hidden="true"
              />
            )}
            {ageChip.label}
            <span className="sr-only">. {ageChip.explanation}</span>
          </li>
        )}
      </ul>
    </section>
  );
};
