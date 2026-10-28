import React, { useId } from "react";
import { Select } from "@/shared/components/ui/Select";
import { STARTS_AT_LABEL, STARTS_AT_QUESTION_ID } from "../../constants/opening";
import { getAnswer, setAnswer } from "../../lib/loreDocument";
import type { StartsAtPickerProps } from "./Guide.types";

const NO_PLACE_VALUE = "";
const MISSING_PLACE_VALUE = "__missing";
const STARTS_AT_QUESTION = { id: STARTS_AT_QUESTION_ID, label: STARTS_AT_LABEL };

export const StartsAtPicker: React.FC<StartsAtPickerProps> = ({ document, places, onChange }) => {
  const fieldId = useId();
  const pickedName = getAnswer(document, STARTS_AT_QUESTION_ID).trim();
  const pickedPlace = places.find((place) => place.name.toLowerCase() === pickedName.toLowerCase());
  const isMissing = pickedName.length > 0 && !pickedPlace;
  const value = pickedPlace?.id ?? (isMissing ? MISSING_PLACE_VALUE : NO_PLACE_VALUE);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    const place = places.find((candidate) => candidate.id === event.target.value);
    onChange(setAnswer(document, STARTS_AT_QUESTION, place?.name ?? ""));
  };

  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="block text-meta font-medium text-content-muted">
        Starts at
      </label>
      <Select
        id={fieldId}
        value={value}
        onChange={handleChange}
        options={[
          { value: NO_PLACE_VALUE, label: "Pick a place (optional)" },
          ...(isMissing ? [{ value: MISSING_PLACE_VALUE, label: `Missing: ${pickedName}` }] : []),
          ...places.map((place) => ({ value: place.id, label: place.name })),
        ]}
      />
    </div>
  );
};
