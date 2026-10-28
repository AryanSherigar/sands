import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Modal } from "@/shared/components/ui/Modal";
import type { OtherTypePromptProps } from "./Guide.types";

const MAX_TYPE_NAME_LENGTH = 60;

export const OtherTypePrompt: React.FC<OtherTypePromptProps> = ({
  isOpen,
  onSubmit,
  onClose,
}) => {
  const [typeName, setTypeName] = useState("");
  const isReady = typeName.trim().length > 0;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!isReady) return;
    onSubmit(typeName.trim());
    setTypeName("");
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="What kind of card is it?" size="narrow">
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block space-y-1 text-meta font-medium text-content-muted">
          Name the kind (creature, event, ship…)
          <Input
            value={typeName}
            maxLength={MAX_TYPE_NAME_LENGTH}
            onChange={(event) => setTypeName(event.target.value)}
            autoFocus
          />
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!isReady}>
            Add
          </Button>
        </div>
      </form>
    </Modal>
  );
};
