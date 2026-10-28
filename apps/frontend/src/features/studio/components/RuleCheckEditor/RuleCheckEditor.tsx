import React, { useMemo, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { EmptyState } from "@/shared/components/ui/EmptyState";
import { Modal } from "@/shared/components/ui/Modal";
import { moveItem } from "@/shared/lib/moveItem";
import { useEntities } from "../../hooks/useEntities";
import { useRuleChecks } from "../../hooks/useRuleChecks";
import { useScenario } from "../../hooks/useScenario";
import { listEnumFields } from "../../lib/stateSchemaFields";
import type {
  RuleCheckCreate,
  RuleCheckResponse,
} from "../../types/ruleCheck.types";
import { buildAvailableFields } from "../ConditionEditor/ExpressionBuilder/availableFields";
import { RuleCheckEditorProps } from "./RuleCheckEditor.types";
import { RuleCheckForm } from "./RuleCheckForm";
import { RuleCheckRow } from "./RuleCheckRow";

export const RuleCheckEditor: React.FC<RuleCheckEditorProps> = ({
  scenarioId,
}) => {
  const { scenario } = useScenario(scenarioId);
  const { entities } = useEntities(scenarioId);
  const {
    checks,
    isLoading,
    createCheck,
    updateCheck,
    deleteCheck,
    reorderChecks,
    isCreating,
    isUpdating,
    createError,
    updateError,
  } = useRuleChecks(scenarioId);
  const [editing, setEditing] = useState<RuleCheckResponse | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const availableFields = useMemo(
    () => buildAvailableFields(scenario?.state_schema ?? {}, entities),
    [scenario, entities],
  );
  const enumFields = useMemo(
    () => listEnumFields(scenario?.state_schema ?? {}),
    [scenario],
  );

  const handleOpenCreate = (): void => {
    setEditing(null);
    setIsFormOpen(true);
  };
  const handleOpenEdit = (check: RuleCheckResponse): void => {
    setEditing(check);
    setIsFormOpen(true);
  };
  const handleCloseForm = (): void => setIsFormOpen(false);

  const handleSubmit = (payload: RuleCheckCreate): void => {
    if (editing) {
      updateCheck(
        { checkId: editing.check_id, payload },
        { onSuccess: handleCloseForm },
      );
      return;
    }
    createCheck(payload, { onSuccess: handleCloseForm });
  };

  const handleMove = (index: number, offset: number): void => {
    const reordered = moveItem(checks, index, index + offset);
    reorderChecks(reordered.map((check) => check.check_id));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-content">Rule checks</h1>
        <Button onClick={handleOpenCreate}>New Rule Check</Button>
      </div>
      {isLoading && <p className="text-sm text-content-faint">Loading rule checks…</p>}
      {!isLoading && checks.length === 0 && (
        <EmptyState
          title="No rule checks yet"
          description="A rule check is a timed prompt the game opens from a tracked value. The answer is written back into a tracked value your active rules can react to."
          example="Example: when the lamp goes out, give the player 12 seconds to hold still or move."
        />
      )}
      <ul className="space-y-2">
        {checks.map((check, index) => (
          <RuleCheckRow
            key={check.check_id}
            check={check}
            index={index}
            total={checks.length}
            onEdit={handleOpenEdit}
            onDelete={deleteCheck}
            onMove={handleMove}
          />
        ))}
      </ul>
      <Modal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        title={editing ? "Edit Rule Check" : "New Rule Check"}
      >
        <RuleCheckForm
          check={editing}
          availableFields={availableFields}
          enumFields={enumFields}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
          isSubmitting={isCreating || isUpdating}
          submitError={editing ? updateError : createError}
        />
      </Modal>
    </div>
  );
};
