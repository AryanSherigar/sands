import React from "react";
import { Input } from "@/shared/components/ui/Input";
import type { NewValueFieldsProps } from "./SentenceBuilder.types";

export const NewValueFields: React.FC<NewValueFieldsProps> = ({ form }) => {
  const { fields, setters } = form;

  if (fields.kind === "enum") {
    return (
      <label className="space-y-1 text-meta text-content-muted">
        Choices, separated by commas
        <Input value={fields.choices} onChange={(event) => setters.setChoices(event.target.value)} />
      </label>
    );
  }
  if (fields.kind !== "number") return null;

  return (
    <>
      <label className="w-24 space-y-1 text-meta text-content-muted">
        Starts at
        <Input type="number" value={fields.startsAt} onChange={(event) => setters.setStartsAt(event.target.value)} />
      </label>
      <label className="w-24 space-y-1 text-meta text-content-muted">
        Lowest
        <Input type="number" value={fields.lowest} onChange={(event) => setters.setLowest(event.target.value)} />
      </label>
      <label className="w-24 space-y-1 text-meta text-content-muted">
        Highest
        <Input type="number" value={fields.highest} onChange={(event) => setters.setHighest(event.target.value)} />
      </label>
    </>
  );
};
