import React from "react";
import type { TerminalFactCardProps } from "./TerminalFactCard.types";

export const TerminalFactCard: React.FC<TerminalFactCardProps> = ({ fact }) => {
  const is_anime = fact.category === "anime";
  const badgeClass = is_anime
    ? "border-purple-500/30 bg-purple-500/10 text-purple-300"
    : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

  return (
    <div className="rounded-md border border-border-subtle bg-surface-raised/80 p-3 text-left font-mono">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-semibold text-content text-sm">{fact.title}</span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] uppercase font-mono tracking-wider border ${badgeClass}`}
        >
          {fact.category}
        </span>
      </div>
      <p className="text-content-muted text-xs leading-relaxed">{fact.fact}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {fact.tags.map((tag) => (
          <span
            key={tag}
            className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] text-content-faint"
          >
            #{tag}
          </span>
        ))}
      </div>
    </div>
  );
};
