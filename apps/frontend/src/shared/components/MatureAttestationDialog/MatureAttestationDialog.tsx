import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { useMatureAttestationStore } from "@/shared/stores/matureAttestation.store";

const ATTESTATION_LABEL = "I confirm I am 18 or older";

export const MatureAttestationDialog: React.FC = () => {
  const isOpen = useMatureAttestationStore((state) => state.isOpen);
  const settle = useMatureAttestationStore((state) => state.settle);
  const [isChecked, setIsChecked] = useState(false);

  const handleClose = (): void => {
    setIsChecked(false);
    settle(false);
  };

  const handleConfirm = (): void => {
    setIsChecked(false);
    settle(true);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Show mature content"
      size="narrow"
    >
      <div className="space-y-4">
        <p className="font-sans text-sm text-content-muted">
          Mature stories may include graphic violence, strong language or other
          content meant for adults.
        </p>
        <label className="flex items-center gap-2.5 font-sans text-sm text-content">
          <input
            type="checkbox"
            checked={isChecked}
            onChange={(event) => setIsChecked(event.target.checked)}
            className="h-4 w-4 accent-[rgb(var(--accent))]"
          />
          {ATTESTATION_LABEL}
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={!isChecked}>
            Show mature content
          </Button>
        </div>
      </div>
    </Modal>
  );
};
