import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { DELETE_CONFIRMATION_PHRASE } from "../../constants/settings.constants";
import { useDeleteAccount } from "../../hooks/useDeleteAccount";
import type { DeleteAccountDialogProps } from "./DeleteAccountDialog.types";

export const DeleteAccountDialog: React.FC<DeleteAccountDialogProps> = ({
  isOpen,
  onClose,
}) => {
  const [typedPhrase, setTypedPhrase] = useState("");
  const { confirmDeletion, isDeleting, errorMessage } = useDeleteAccount();
  const isPhraseMatched = typedPhrase === DELETE_CONFIRMATION_PHRASE;

  const handleClose = (): void => {
    setTypedPhrase("");
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Delete account"
      size="narrow"
      isDismissible={!isDeleting}
    >
      <div className="space-y-4 font-sans text-sm text-content-muted">
        <p>
          Your account is deactivated immediately. After 30 days your profile,
          playthroughs, reviews and bookmarks are permanently deleted, and your
          published scenarios are kept under &ldquo;Deleted user&rdquo;. Signing
          back in within 30 days cancels the deletion.
        </p>
        <p>
          You&apos;ll be asked to sign in with Google again to confirm it&apos;s you.
        </p>
        <div className="space-y-2">
          <label
            htmlFor="delete-confirmation"
            className="block text-xs font-medium text-content"
          >
            Type {DELETE_CONFIRMATION_PHRASE} to confirm
          </label>
          <input
            id="delete-confirmation"
            value={typedPhrase}
            autoComplete="off"
            onChange={(event) => setTypedPhrase(event.target.value)}
            className="h-10 w-full rounded-sm border border-border-strong bg-surface-inset px-3 font-mono text-sm text-content focus-visible:border-primary focus-visible:outline-hidden"
          />
        </div>
        {errorMessage && (
          <p role="alert" className="text-xs text-danger">
            {errorMessage}
          </p>
        )}
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={handleClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="danger"
            disabled={!isPhraseMatched || isDeleting}
            onClick={() => void confirmDeletion()}
          >
            {isDeleting ? "Deleting…" : "Delete my account"}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
