import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import {
  CARD_VALUES_EMPTY_COPY,
  CARD_VALUES_HEADING,
  CARD_VALUES_HELPER,
  CARD_VALUE_ADD_LABEL,
  CARD_VALUE_NAME_LABEL,
} from "../../constants/cardValues";
import { useCardValues } from "../../hooks/useCardValues";
import type { CardValuesProps } from "./Card.types";
import { CardValueCard } from "./CardValueCard";

export const CardValues: React.FC<CardValuesProps> = ({ scenarioId, entity }) => {
  const { attributes, writeValue, addValue, removeValue } = useCardValues(scenarioId, entity);
  const [newName, setNewName] = useState("");
  const entries = Object.entries(attributes);
  const canAdd = newName.trim().length > 0;

  const handleAdd = (event: React.FormEvent): void => {
    event.preventDefault();
    if (!canAdd) return;
    addValue(newName, "number");
    setNewName("");
  };

  return (
    <section aria-label={CARD_VALUES_HEADING} className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-meta font-medium text-content-muted">{CARD_VALUES_HEADING}</h3>
        <p className="text-micro text-content-faint">{CARD_VALUES_HELPER}</p>
      </div>
      {entries.length === 0 && <p className="text-meta text-content-muted">{CARD_VALUES_EMPTY_COPY}</p>}
      {entries.map(([key, attribute]) => (
        <CardValueCard
          key={key}
          entityId={entity.entity_id}
          valueKey={key}
          attribute={attribute}
          onChange={(next) => writeValue(key, next)}
          onDelete={() => removeValue(key)}
        />
      ))}
      <form onSubmit={handleAdd} className="flex items-end gap-2">
        <label className="block flex-1 space-y-1 text-meta text-content-muted">
          {CARD_VALUE_NAME_LABEL}
          <Input value={newName} placeholder="Trust" onChange={(event) => setNewName(event.target.value)} />
        </label>
        <Button type="submit" size="sm" variant="secondary" disabled={!canAdd}>
          {CARD_VALUE_ADD_LABEL}
        </Button>
      </form>
    </section>
  );
};
