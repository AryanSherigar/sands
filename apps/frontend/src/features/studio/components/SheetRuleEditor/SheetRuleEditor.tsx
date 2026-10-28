import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { EmptyState } from "@/shared/components/ui/EmptyState";
import { Modal } from "@/shared/components/ui/Modal";
import { moveItem } from "@/shared/lib/moveItem";
import { useSheetRules } from "../../hooks/useSheetRules";
import type {
  SheetRuleCreate,
  SheetRuleResponse,
} from "../../types/sheetRule.types";
import { ClipboardPreview } from "./ClipboardPreview";
import { SheetRuleEditorProps } from "./SheetRuleEditor.types";
import { SheetRuleForm } from "./SheetRuleForm";
import { SheetRuleRow } from "./SheetRuleRow";

export const SheetRuleEditor: React.FC<SheetRuleEditorProps> = ({
  scenarioId,
}) => {
  const {
    rules,
    isLoading,
    createRule,
    updateRule,
    deleteRule,
    reorderRules,
    isCreating,
    isUpdating,
    createError,
    updateError,
  } = useSheetRules(scenarioId);
  const [editing, setEditing] = useState<SheetRuleResponse | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const nextNumber = Math.max(0, ...rules.map((rule) => rule.number)) + 1;

  const handleOpenCreate = (): void => {
    setEditing(null);
    setIsFormOpen(true);
  };
  const handleOpenEdit = (rule: SheetRuleResponse): void => {
    setEditing(rule);
    setIsFormOpen(true);
  };
  const handleCloseForm = (): void => setIsFormOpen(false);

  const handleSubmit = (payload: SheetRuleCreate): void => {
    if (editing) {
      const { key: _key, ...changes } = payload;
      updateRule(
        { ruleId: editing.rule_id, payload: changes },
        { onSuccess: handleCloseForm },
      );
      return;
    }
    createRule(payload, { onSuccess: handleCloseForm });
  };

  const handleMove = (index: number, offset: number): void => {
    const reordered = moveItem(rules, index, index + offset);
    reorderRules(reordered.map((rule) => rule.rule_id));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-content">Rule sheet</h1>
        <Button onClick={handleOpenCreate}>New Rule</Button>
      </div>
      {isLoading && <p className="text-sm text-content-faint">Loading rules…</p>}
      {!isLoading && rules.length === 0 && (
        <EmptyState
          title="No rules yet"
          description="These are the rules on the player's clipboard. Their status changes as the story plays."
          example="Example: Rule 1, typed: Every visitor signs the Log."
        />
      )}
      <ul className="space-y-2">
        {rules.map((rule, index) => (
          <SheetRuleRow
            key={rule.rule_id}
            rule={rule}
            index={index}
            total={rules.length}
            onEdit={handleOpenEdit}
            onDelete={deleteRule}
            onMove={handleMove}
          />
        ))}
      </ul>
      {rules.length > 0 && <ClipboardPreview rules={rules} />}
      <Modal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        title={editing ? "Edit Rule" : "New Rule"}
      >
        <SheetRuleForm
          rule={editing}
          existingKeys={rules.map((rule) => rule.key)}
          nextNumber={nextNumber}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
          isSubmitting={isCreating || isUpdating}
          submitError={editing ? updateError : createError}
        />
      </Modal>
    </div>
  );
};
