import React from "react";
import { Select } from "@/shared/components/ui/Select";
import type { MeterTier } from "@/shared/types/display-hints.types";
import {
  BAR_NEEDS_BOUNDS_NOTE,
  CLOCK_TAKEN_NOTE,
  LEVELS_TAKEN_NOTE,
  PLAYER_SEES_LABEL,
} from "../../../constants/trackedValues";
import {
  applyPlayerSees,
  hasBounds,
  listPlayerSeesChoices,
  readPlayerSees,
  type PlayerSees,
} from "../../../lib/trackedValueEditing";
import type { StateFieldDefinition } from "../../../types/scenario.types";
import type { PlayerSeesFieldsProps } from "./Advanced.types";
import { ClockFields } from "./ClockFields";
import { LevelsEditor } from "./LevelsEditor";

const SEES_LABELS: Record<PlayerSees, string> = {
  bar: "Bar",
  plain: "Number",
  levels: "Levels",
  clock: "Clock",
  hidden: "Hidden",
};

const labelFor = (sees: PlayerSees, field: StateFieldDefinition): string =>
  sees === "plain" && field.type !== "number" ? "Plain value" : SEES_LABELS[sees];

const readTiers = (field: StateFieldDefinition): MeterTier[] =>
  Array.isArray(field.display?.tiers) ? (field.display.tiers as MeterTier[]) : [];

export const PlayerSeesFields: React.FC<PlayerSeesFieldsProps> = ({ field, availability, onChange }) => {
  const current = readPlayerSees(field);
  const choices = listPlayerSeesChoices(field, availability);
  const options = choices
    .filter((choice) => !choice.isDisabled)
    .map((choice) => ({ value: choice.value, label: labelFor(choice.value, field) }));
  const isBarBlocked = field.type === "number" && !hasBounds(field);

  return (
    <div className="space-y-2">
      <label className="block max-w-56 space-y-1 text-meta text-content-muted">
        {PLAYER_SEES_LABEL}
        <Select
          value={current}
          options={options}
          onChange={(event) => onChange(applyPlayerSees(field, event.target.value as PlayerSees))}
        />
      </label>
      {isBarBlocked && <p className="text-micro text-content-faint">{BAR_NEEDS_BOUNDS_NOTE}</p>}
      {availability.isClockTaken && current !== "clock" && field.type === "number" && (
        <p className="text-micro text-content-faint">{CLOCK_TAKEN_NOTE}</p>
      )}
      {availability.isLevelsTaken && current !== "levels" && field.type === "enum" && (
        <p className="text-micro text-content-faint">{LEVELS_TAKEN_NOTE}</p>
      )}
      {current === "levels" && field.type === "number" && (
        <LevelsEditor
          tiers={readTiers(field)}
          onChange={(tiers) => onChange({ ...field, display: { ...field.display, tiers } })}
        />
      )}
      {current === "levels" && field.type === "enum" && (
        <p className="text-micro text-content-faint">Each choice becomes a level, in order.</p>
      )}
      {current === "clock" && <ClockFields field={field} onChange={onChange} />}
    </div>
  );
};
