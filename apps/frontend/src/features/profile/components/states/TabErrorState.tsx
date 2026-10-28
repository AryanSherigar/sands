import React from "react";
import { IconAlertCircle } from "@tabler/icons-react";
import type { TabErrorStateProps } from "./TabErrorState.types";

export const TabErrorState: React.FC<TabErrorStateProps> = ({ message }) => (
  <div
    role="alert"
    className="flex items-center justify-center gap-2 rounded-md border border-danger/30 bg-surface-raised px-4 py-10 text-sm text-danger"
  >
    <IconAlertCircle size={20} stroke={1.5} aria-hidden="true" />
    <span>{message}</span>
  </div>
);
