import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import type { CampaignAbandonControlProps } from "./CampaignCard.types";

export const CampaignAbandonControl: React.FC<CampaignAbandonControlProps> = ({
  onConfirm,
  isAbandoning,
}) => {
  const [isConfirming, setIsConfirming] = useState(false);

  const handleConfirm = () => {
    onConfirm();
    setIsConfirming(false);
  };

  if (!isConfirming) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setIsConfirming(true)}>
        Abandon
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-danger">Abandon run?</span>
      <Button
        variant="danger"
        size="sm"
        onClick={handleConfirm}
        disabled={isAbandoning}
      >
        Yes
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setIsConfirming(false)}>
        No
      </Button>
    </div>
  );
};
