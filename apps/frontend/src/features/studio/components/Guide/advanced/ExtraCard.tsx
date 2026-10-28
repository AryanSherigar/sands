import React, { useState } from "react";
import { IconCheck } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import {
  EXTRA_ACKNOWLEDGE_LABEL,
  EXTRA_ADD_LABEL,
  EXTRA_CANCEL_LABEL,
  EXTRA_EDIT_LABEL,
  EXTRA_KEPT_MESSAGE,
  EXTRA_ON_LABEL,
  EXTRA_REMOVE_LABEL,
  EXTRA_STILL_USED_MESSAGE,
  EXTRA_TURN_OFF_LABEL,
  formatExtraTurnOffQuestion,
} from "../../../constants/extras";
import type { ExtraCardProps } from "./Advanced.types";

export const ExtraCard: React.FC<ExtraCardProps> = ({
  extra,
  isOn,
  removal,
  onAdd,
  onEdit,
  onRemove,
}) => {
  const [isConfirmingRemove, setIsConfirmingRemove] = useState(false);
  const isStillUsed = removal?.state === "in_use";

  const handleClose = (): void => setIsConfirmingRemove(false);
  const handleConfirmRemove = (): void => {
    handleClose();
    onRemove();
  };

  return (
    <article
      aria-label={`Extra ${extra.name}`}
      className="flex flex-col justify-between gap-4 rounded-lg border border-border-subtle bg-surface-raised p-4"
    >
      <header className="space-y-1">
        <div className="flex items-center gap-2">
          <h3 className="text-heading font-semibold text-content">{extra.name}</h3>
          {isOn && (
            <span className="flex items-center gap-1 rounded-sm border border-border-strong px-1.5 py-0.5 text-micro text-content-muted">
              <IconCheck size={12} aria-hidden="true" />
              {EXTRA_ON_LABEL}
            </span>
          )}
        </div>
        <p className="text-meta text-content-muted">{extra.description}</p>
      </header>
      <div className="flex flex-wrap gap-2">
        {isOn ? (
          <Button type="button" size="sm" variant="secondary" onClick={onEdit}>
            {EXTRA_EDIT_LABEL}
          </Button>
        ) : (
          <Button type="button" size="sm" onClick={onAdd}>
            {EXTRA_ADD_LABEL}
          </Button>
        )}
        {isOn && removal && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={removal.state === "checking"}
            onClick={() => setIsConfirmingRemove(true)}
          >
            {EXTRA_REMOVE_LABEL}
          </Button>
        )}
      </div>
      {removal && (
        <Modal
          isOpen={isConfirmingRemove}
          onClose={handleClose}
          title={formatExtraTurnOffQuestion(removal.toolName)}
          size="narrow"
        >
          <div className="space-y-4">
            <p className="text-body text-content-muted">
              {isStillUsed ? EXTRA_STILL_USED_MESSAGE : EXTRA_KEPT_MESSAGE}
            </p>
            <div className="flex justify-end gap-2">
              {isStillUsed ? (
                <Button variant="secondary" onClick={handleClose}>
                  {EXTRA_ACKNOWLEDGE_LABEL}
                </Button>
              ) : (
                <>
                  <Button variant="ghost" onClick={handleClose}>
                    {EXTRA_CANCEL_LABEL}
                  </Button>
                  <Button variant="danger" onClick={handleConfirmRemove}>
                    {EXTRA_TURN_OFF_LABEL}
                  </Button>
                </>
              )}
            </div>
          </div>
        </Modal>
      )}
    </article>
  );
};
