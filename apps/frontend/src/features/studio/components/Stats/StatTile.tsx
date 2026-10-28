import React from "react";
import type { StatTileProps } from "./StatTile.types";

export const StatTile: React.FC<StatTileProps> = ({ label, value, footnote }) => (
  <div className="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-raised p-4">
    <span className="font-mono text-3xl tabular-nums text-content">{value}</span>
    <span className="font-sans text-sm text-content-muted">{label}</span>
    {footnote}
  </div>
);
