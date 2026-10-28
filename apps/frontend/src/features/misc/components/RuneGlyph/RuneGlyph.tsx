import React from "react";
import type { RuneGlyphProps } from "./RuneGlyph.types";
import { ArcaneRuneIcon } from "./ArcaneRuneIcon";

export const RuneGlyph: React.FC<RuneGlyphProps> = ({
  onActivate,
  is_active = false,
}) => {
  const activeClass = is_active ? "border-accent shadow-accent-glow" : "";

  return (
    <button
      type="button"
      onClick={onActivate}
      aria-label="Commune with the arcane rune"
      className="group relative flex flex-col items-center gap-2 rounded-xl p-3 transition duration-300 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      <div
        className={`relative flex h-12 w-12 items-center justify-center rounded-full border border-accent/40 bg-surface-raised transition duration-500 group-hover:scale-110 group-hover:border-accent group-hover:shadow-accent-glow ${activeClass}`}
      >
        <ArcaneRuneIcon />
      </div>
      <span className="font-mono text-[11px] text-content-faint transition duration-300 group-hover:text-accent">
        ✦ commune [~] ✦
      </span>
    </button>
  );
};
