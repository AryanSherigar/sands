import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { DELETE_LABEL } from "../../constants/advancedCards";
import { CARD_VALUE_KIND_OPTIONS, CARD_VALUE_NARRATOR_LABEL } from "../../constants/cardValues";
import { FULL_EDITOR_VALUE_NOTE, formatInUseQuestion } from "../../constants/trackedValues";
import { useUsedIn } from "../../hooks/useUsedIn";
import {
  buildCardValuePath,
  isEditableCardValue,
  toAttribute,
  toValueField,
} from "../../lib/cardValues";
import { changeKind } from "../../lib/trackedValueEditing";
import { humanizeKey } from "../../lib/valueOptions";
import type { StateFieldDefinition } from "../../types/scenario.types";
import type { ValueKind } from "../../types/sentence.types";
import { AdvancedCard } from "../Guide/advanced/AdvancedCard";
import { DeleteValueDialog } from "../Guide/advanced/DeleteValueDialog";
import { TrackedValueFields } from "../Guide/advanced/TrackedValueFields";
import { UsedInList } from "../Guide/advanced/UsedInList";
import type { CardValueCardProps } from "./Card.types";

export const CardValueCard: React.FC<CardValueCardProps> = ({
  entityId,
  valueKey,
  attribute,
  onChange,
  onDelete,
}) => {
  const path = buildCardValuePath(entityId, valueKey);
  const usedIn = useUsedIn(path);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const name = attribute.label?.trim() || humanizeKey(valueKey);
  const field = toValueField(attribute);

  const handleFieldChange = (next: StateFieldDefinition): void => onChange(toAttribute(next, attribute));
  const handleDeleteRequest = (): void => {
    if (usedIn.total > 0) setIsConfirmingDelete(true);
    else onDelete();
  };
  const handleConfirmDelete = (): void => {
    setIsConfirmingDelete(false);
    onDelete();
  };

  if (!isEditableCardValue(attribute)) {
    return (
      <p className="rounded-md border border-border-subtle bg-surface-inset px-3 py-2 text-meta text-content-muted">
        {name} · {FULL_EDITOR_VALUE_NOTE}
      </p>
    );
  }

  return (
    <AdvancedCard
      ariaLabel={`Value ${name}`}
      badge="Value"
      menuLabel={`${name} options`}
      menuItems={[{ id: "delete", label: DELETE_LABEL, isDanger: true, onSelect: handleDeleteRequest }]}
    >
      <div className="flex items-end gap-3">
        <label className="block flex-1 space-y-1 text-meta font-medium text-content-muted">
          Name
          <Input
            value={attribute.label ?? ""}
            onChange={(event) => handleFieldChange({ ...field, label: event.target.value })}
          />
        </label>
        <label className="block w-36 space-y-1 text-meta font-medium text-content-muted">
          Type
          <Select
            value={attribute.type}
            options={[...CARD_VALUE_KIND_OPTIONS]}
            onChange={(event) => handleFieldChange(changeKind(field, event.target.value as ValueKind))}
          />
        </label>
      </div>
      <TrackedValueFields field={field} onChange={handleFieldChange} />
      <label className="flex items-center gap-2 text-meta text-content-muted">
        <input
          type="checkbox"
          checked={attribute.is_narrator_visible ?? false}
          onChange={(event) => onChange({ ...attribute, is_narrator_visible: event.target.checked })}
        />
        {CARD_VALUE_NARRATOR_LABEL}
      </label>
      <UsedInList valueKey={path} />
      <DeleteValueDialog
        isOpen={isConfirmingDelete}
        question={formatInUseQuestion(name, usedIn.total)}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsConfirmingDelete(false)}
      />
    </AdvancedCard>
  );
};
