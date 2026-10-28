import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { NEW_VALUE_KIND_OPTIONS } from "../../../constants/sentenceBuilder";
import {
  NEEDS_DETAILS_LABEL,
  VALUE_TYPE_LABEL,
  WHAT_IT_MEANS_HELPER,
  WHAT_IT_MEANS_LABEL,
  formatInUseQuestion,
  formatTypeChangeQuestion,
} from "../../../constants/trackedValues";
import { DELETE_LABEL } from "../../../constants/advancedCards";
import { useUsedIn } from "../../../hooks/useUsedIn";
import { changeKind, isNeedingDetails, renameField } from "../../../lib/trackedValueEditing";
import { humanizeKey } from "../../../lib/valueOptions";
import type { ValueKind } from "../../../types/sentence.types";
import { AdvancedCard } from "./AdvancedCard";
import { DeleteValueDialog } from "./DeleteValueDialog";
import { FieldBlock } from "./FieldBlock";
import { PlayerSeesFields } from "./PlayerSeesFields";
import { TrackedValueFields } from "./TrackedValueFields";
import type { TrackedValueCardProps } from "./Advanced.types";
import { UsedInList } from "./UsedInList";

export const TrackedValueCard: React.FC<TrackedValueCardProps> = ({
  valueKey,
  field,
  availability,
  onChange,
  onDelete,
}) => {
  const usedIn = useUsedIn(valueKey);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [pendingKind, setPendingKind] = useState<ValueKind | null>(null);
  const name = field.label?.trim() || humanizeKey(valueKey);

  const handleDeleteRequest = (): void => {
    if (usedIn.total > 0) setIsConfirmingDelete(true);
    else onDelete();
  };
  const handleConfirmDelete = (): void => {
    setIsConfirmingDelete(false);
    onDelete();
  };

  const handleKindChange = (kind: ValueKind): void => {
    if (usedIn.total > 0) setPendingKind(kind);
    else onChange(changeKind(field, kind));
  };
  const handleConfirmKind = (): void => {
    if (pendingKind) onChange(changeKind(field, pendingKind));
    setPendingKind(null);
  };

  return (
    <AdvancedCard
      ariaLabel={`Tracked value ${name}`}
      badge="Tracked value"
      menuLabel={`${name} options`}
      menuItems={[{ id: "delete", label: DELETE_LABEL, isDanger: true, onSelect: handleDeleteRequest }]}
    >
      <div className="flex items-end gap-3">
        <label className="block flex-1 space-y-1 text-meta font-medium text-content-muted">
          Name
          <Input value={field.label ?? ""} onChange={(event) => onChange(renameField(field, event.target.value))} />
        </label>
        <label className="block w-40 space-y-1 text-meta font-medium text-content-muted">
          {VALUE_TYPE_LABEL}
          <Select
            value={field.type}
            options={NEW_VALUE_KIND_OPTIONS}
            onChange={(event) => handleKindChange(event.target.value as ValueKind)}
          />
        </label>
        {isNeedingDetails(field) && (
          <span className="mb-2 rounded-sm border border-border-strong px-2 py-0.5 text-micro text-warning">
            {NEEDS_DETAILS_LABEL}
          </span>
        )}
      </div>
      <TrackedValueFields field={field} onChange={onChange} />
      <FieldBlock label={WHAT_IT_MEANS_LABEL} helper={WHAT_IT_MEANS_HELPER}>
        <Input
          aria-label={WHAT_IT_MEANS_LABEL}
          value={field.description ?? ""}
          onChange={(event) => onChange({ ...field, description: event.target.value })}
        />
      </FieldBlock>
      <PlayerSeesFields field={field} availability={availability} onChange={onChange} />
      <UsedInList valueKey={valueKey} />
      <DeleteValueDialog
        isOpen={isConfirmingDelete}
        title="Delete value"
        confirmLabel="Delete"
        question={formatInUseQuestion(name, usedIn.total)}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsConfirmingDelete(false)}
      />
      <DeleteValueDialog
        isOpen={pendingKind !== null}
        title="Change type"
        confirmLabel="Change type"
        question={formatTypeChangeQuestion(name, usedIn.total)}
        onConfirm={handleConfirmKind}
        onCancel={() => setPendingKind(null)}
      />
    </AdvancedCard>
  );
};
