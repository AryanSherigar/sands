import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { DeleteAccountDialog } from "../DeleteAccountDialog/DeleteAccountDialog";

export const DangerZoneSection: React.FC = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-danger/30 bg-surface-raised p-5">
      <div className="space-y-1">
        <p className="font-sans text-sm font-medium text-danger">Delete account</p>
        <p className="max-w-sm font-sans text-xs text-content-faint">
          Permanently remove your account, saves and unpublished scenario
          drafts after a 30-day grace period.
        </p>
      </div>
      <Button variant="danger" onClick={() => setIsDialogOpen(true)}>
        Delete account…
      </Button>
      <DeleteAccountDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
      />
    </div>
  );
};
