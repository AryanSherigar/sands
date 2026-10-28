import React from "react";
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconArchive,
  IconCircleCheck,
  IconLoader2,
  IconPencil,
  type Icon,
} from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import type { DisplayStatus } from "../../utils/scenarioRowStatus";
import type { ScenarioStatusBadgeProps } from "./StudioList.types";

interface StatusPresentation {
  label: string;
  StatusIcon: Icon;
  toneClass: string;
}

const STATUS_PRESENTATION: Record<DisplayStatus, StatusPresentation> = {
  draft: { label: "Draft", StatusIcon: IconPencil, toneClass: "text-content-faint" },
  publishing: {
    label: "Publishing…",
    StatusIcon: IconLoader2,
    toneClass: "text-warning",
  },
  published: {
    label: "Published",
    StatusIcon: IconCircleCheck,
    toneClass: "text-success",
  },
  published_changes: {
    label: "Published — changes not yet published",
    StatusIcon: IconAlertTriangle,
    toneClass: "text-warning",
  },
  publish_failed: {
    label: "Publish failed",
    StatusIcon: IconAlertCircle,
    toneClass: "text-danger",
  },
  archived: {
    label: "Archived",
    StatusIcon: IconArchive,
    toneClass: "text-content-faint",
  },
};

export const ScenarioStatusBadge: React.FC<ScenarioStatusBadgeProps> = ({
  status,
}) => {
  const { label, StatusIcon, toneClass } = STATUS_PRESENTATION[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm bg-surface-inset px-2 py-0.5 font-sans text-xs font-medium",
        toneClass,
      )}
    >
      <StatusIcon
        size={14}
        aria-hidden="true"
        className={status === "publishing" ? "motion-safe:animate-spin" : ""}
      />
      {label}
    </span>
  );
};
