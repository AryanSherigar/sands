import React from "react";
import { IconLock } from "@tabler/icons-react";
import type { LockedEndingSlotProps } from "./LockedEndingSlot.types";

export const LockedEndingSlot: React.FC<LockedEndingSlotProps> = ({
  position,
}) => (
  <li className="flex items-center justify-between rounded-md border border-dashed border-border-subtle bg-surface-inset/60 p-4 font-mono text-xs text-content-faint">
    <span>Ending #{position}</span>
    <span className="flex items-center gap-1.5">
      <IconLock size={16} stroke={1.5} aria-hidden="true" />
      <span className="sr-only">Not found yet</span>
    </span>
  </li>
);
