import React from "react";
import { Select, type SelectOption, type SelectOptionGroup } from "@/shared/components/ui/Select";
import {
  CARD_GROUP_LABEL,
  NEW_VALUE_LABEL,
  NEW_VALUE_OPTION,
  NO_SELECTION,
  TRACKED_GROUP_LABEL,
  VALUE_PLACEHOLDER,
} from "../../constants/sentenceBuilder";
import type { ValueOption } from "../../types/sentence.types";
import type { ValuePickerProps } from "./SentenceBuilder.types";

const toSelectOption = (option: ValueOption): SelectOption => ({
  value: option.path,
  label: option.label,
});

const buildGroups = (options: ValueOption[]): SelectOptionGroup[] => {
  const tracked = options.filter((option) => option.source === "tracked");
  const cards = options.filter((option) => option.source === "card");
  return [
    { label: TRACKED_GROUP_LABEL, options: tracked.map(toSelectOption) },
    { label: CARD_GROUP_LABEL, options: cards.map(toSelectOption) },
  ].filter((group) => group.options.length > 0);
};

export const ValuePicker: React.FC<ValuePickerProps> = ({
  path,
  options,
  missingName,
  label,
  onSelect,
  onRequestNew,
}) => {
  const leading: SelectOption[] = [{ value: NO_SELECTION, label: VALUE_PLACEHOLDER }];
  if (missingName !== null) {
    leading.push({ value: path, label: missingName });
  }
  leading.push({ value: NEW_VALUE_OPTION, label: NEW_VALUE_LABEL });

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    if (event.target.value === NEW_VALUE_OPTION) onRequestNew();
    else onSelect(event.target.value);
  };

  return (
    <Select
      aria-label={label}
      className="w-auto min-w-40"
      value={path}
      options={leading}
      groups={buildGroups(options)}
      onChange={handleChange}
    />
  );
};
