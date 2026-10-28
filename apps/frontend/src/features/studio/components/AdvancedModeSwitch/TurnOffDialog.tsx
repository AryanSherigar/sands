import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import {
  ADVANCED_TURN_OFF_CONFIRM_LABEL,
  ADVANCED_TURN_OFF_COPY,
  ADVANCED_TURN_OFF_TITLE,
  buildMissingPublishWarning,
} from "../../constants/advancedMode";
import type { TurnOffDialogProps } from "./TurnOffDialog.types";

export const TurnOffDialog: React.FC<TurnOffDialogProps> = ({
  isOpen,
  isBusy,
  missingPublishItems = [],
  onConfirm,
  onCancel,
}) => (
  <Modal isOpen={isOpen} onClose={onCancel} title={ADVANCED_TURN_OFF_TITLE} size="narrow">
    <div className="space-y-6">
      <p className="text-body text-content-muted">{ADVANCED_TURN_OFF_COPY}</p>
      {missingPublishItems.length > 0 && (
        <p role="note" className="text-body text-content">
          {buildMissingPublishWarning(missingPublishItems)}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" disabled={isBusy} onClick={onConfirm}>
          {ADVANCED_TURN_OFF_CONFIRM_LABEL}
        </Button>
      </div>
    </div>
  </Modal>
);
