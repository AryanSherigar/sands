import React from "react";
import { Select } from "@/shared/components/ui/Select";
import { JOINER_OPTIONS } from "../../constants/sentenceBuilder";
import type { SentenceJoiner } from "../../types/sentence.types";
import type { JoinerPickerProps } from "./SentenceBuilder.types";

export const JoinerPicker: React.FC<JoinerPickerProps> = ({ joiner, onChange }) => (
  <label className="flex items-center gap-2 text-meta text-content-muted">
    Join rows with
    <Select
      aria-label="Join rows with"
      className="w-auto"
      value={joiner}
      options={JOINER_OPTIONS}
      onChange={(event) => onChange(event.target.value as SentenceJoiner)}
    />
  </label>
);
