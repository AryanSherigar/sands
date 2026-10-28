import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import type { DeleteValueDialogProps } from "./Advanced.types";

export const DeleteValueDialog: React.FC<DeleteValueDialogProps> = ({
  isOpen,
  title = "Delete value",
  confirmLabel = "Delete",
  question,
  onConfirm,
  onCancel,
}) => (
  <Modal isOpen={isOpen} onClose={onCancel} title={title} size="narrow">
    <div className="space-y-4">
      <p className="text-sm text-content">{question}</p>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </div>
  </Modal>
);
