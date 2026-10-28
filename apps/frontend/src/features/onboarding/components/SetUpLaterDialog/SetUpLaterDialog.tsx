import React from "react";
import { Modal } from "@/shared/components/ui/Modal";
import type { SetUpLaterDialogProps } from "./SetUpLaterDialog.types";

export const SetUpLaterDialog: React.FC<SetUpLaterDialogProps> = ({
  isOpen,
  isSaving,
  errorMessage,
  onConfirm,
  onCancel,
}) => (
  <Modal isOpen={isOpen} onClose={onCancel} title="Set up later?" size="narrow">
    <p className="text-sm leading-relaxed text-content-muted">
      You can explore right now with default preferences. We&apos;ll leave a
      quiet reminder on your home feed whenever you want to customize your
      genres and profile.
    </p>
    {errorMessage && (
      <p role="alert" className="mt-3 text-sm text-danger">
        {errorMessage}
      </p>
    )}
    <div className="mt-5 flex items-center justify-end gap-2.5">
      <button
        type="button"
        onClick={onCancel}
        disabled={isSaving}
        className="rounded-md px-3.5 py-1.5 text-xs text-content-muted transition-colors hover:bg-white/6 hover:text-content"
      >
        Keep going
      </button>
      <button
        type="button"
        onClick={onConfirm}
        disabled={isSaving}
        className="rounded-md bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-contrast transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        {isSaving ? "Saving..." : "Set up later"}
      </button>
    </div>
  </Modal>
);
