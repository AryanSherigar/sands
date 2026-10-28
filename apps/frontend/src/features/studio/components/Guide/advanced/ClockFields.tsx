import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { CLOCK_FORMAT_OPTIONS } from "../../../constants/valueQuickAdd";
import type { ClockFieldsProps } from "./Advanced.types";

export const ClockFields: React.FC<ClockFieldsProps> = ({ field, onChange }) => {
  const display = field.display ?? {};
  const patch = (next: Record<string, unknown>): void => onChange({ ...field, display: { ...display, ...next } });

  return (
    <div className="grid grid-cols-2 gap-3">
      <label className="block space-y-1 text-meta text-content-muted">
        Clock starts at
        <Input type="time" value={String(display.start ?? "")} onChange={(event) => patch({ start: event.target.value })} />
      </label>
      <label className="block space-y-1 text-meta text-content-muted">
        Clock style
        <Select
          value={String(display.format ?? "12h")}
          options={[...CLOCK_FORMAT_OPTIONS]}
          onChange={(event) => patch({ format: event.target.value })}
        />
      </label>
    </div>
  );
};
