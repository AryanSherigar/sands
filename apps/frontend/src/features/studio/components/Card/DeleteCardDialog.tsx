import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import type { DeleteCardDialogProps } from "./Card.types";

const formatLinkCount = (count: number): string =>
  count === 1 ? "1 link" : `${count} links`;

export const DeleteCardDialog: React.FC<DeleteCardDialogProps> = ({
  isOpen,
  cardName,
  linkSentences,
  isDeleting,
  onConfirm,
  onCancel,
}) => {
  const hasLinks = linkSentences.length > 0;
  const question = hasLinks
    ? `${cardName} has ${formatLinkCount(linkSentences.length)}. Delete anyway?`
    : `Delete ${cardName}?`;

  return (
    <Modal isOpen={isOpen} onClose={onCancel} title="Delete card" size="narrow">
      <div className="space-y-4">
        <p className="text-sm text-content">{question}</p>
        {hasLinks && (
          <ul className="space-y-1 text-meta text-content-muted">
            {linkSentences.map((sentence) => (
              <li key={sentence}>{sentence}</li>
            ))}
          </ul>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" disabled={isDeleting} onClick={onConfirm}>
            Delete
          </Button>
        </div>
      </div>
    </Modal>
  );
};
