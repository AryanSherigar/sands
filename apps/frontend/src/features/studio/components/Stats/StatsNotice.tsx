import React from "react";
import type { StatsNoticeProps } from "./StatsNotice.types";

export const StatsNotice: React.FC<StatsNoticeProps> = ({
  title,
  description,
  children,
}) => (
  <div
    role="status"
    className="flex flex-col items-start gap-3 rounded-lg border border-border-subtle bg-surface-raised p-6"
  >
    <p className="font-sans text-base font-semibold text-content">{title}</p>
    <p className="font-sans text-sm text-content-muted">{description}</p>
    {children}
  </div>
);
