import React from "react";
import {
  IconCircleOff,
  IconSkull,
  IconTrophy,
} from "@tabler/icons-react";
import type { CampaignStatusProps } from "./CampaignCard.types";

const CHIP_CLASSES =
  "inline-flex items-center gap-1.5 rounded-sm border border-border-subtle bg-surface-inset px-2 py-0.5 text-xs font-medium text-content";

export const CampaignStatus: React.FC<CampaignStatusProps> = ({ campaign }) => {
  if (campaign.status === "active") {
    return (
      <span className={CHIP_CLASSES}>
        <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
        In progress
      </span>
    );
  }
  if (campaign.status === "abandoned") {
    return (
      <span className={CHIP_CLASSES}>
        <IconCircleOff size={16} stroke={1.5} aria-hidden="true" />
        Abandoned
      </span>
    );
  }
  const isWin = campaign.ended_outcome_tag === "win";
  const OutcomeIcon = isWin ? IconTrophy : IconSkull;
  return (
    <span className={CHIP_CLASSES}>
      <OutcomeIcon size={16} stroke={1.5} aria-hidden="true" />
      {isWin ? "Victory" : "Defeat"}
    </span>
  );
};
