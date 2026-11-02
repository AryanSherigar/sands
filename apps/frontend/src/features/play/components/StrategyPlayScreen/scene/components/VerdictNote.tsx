import React from "react";
import type { VerdictNoteProps } from "./VerdictNote.types";

interface VerdictCopy {
  chip: string;
  sentence: string;
  chipClass: string;
}

const VERDICT_COPY: Record<string, VerdictCopy> = {
  accept: {
    chip: "Will sign",
    sentence: "They will put their seal to these terms.",
    chipClass: "bg-meadow-green/20 text-meadow-green",
  },
  haggle: {
    chip: "Will bargain",
    sentence: "Not enough yet. Ease a demand or sweeten an offer.",
    chipClass: "bg-amber-500/20 text-amber-300",
  },
  refuse: {
    chip: "Refuses",
    sentence: "These terms are far from what they would accept.",
    chipClass: "bg-[#A8483E]/20 text-rose-300",
  },
};

export const VerdictNote: React.FC<VerdictNoteProps> = ({ verdict, hasProposal }) => {
  const copy = verdict ? VERDICT_COPY[verdict] : undefined;
  if (!copy) return null;
  if (verdict === "accept" && !hasProposal) return null;
  return (
    <div
      className="flex items-center gap-2 mb-3 p-2.5 rounded-lg bg-surface-container-lowest/60 border border-outline-variant/20"
      role="status"
    >
      <span
        className={`font-sans text-[10px] uppercase px-2 py-0.5 font-bold rounded ${copy.chipClass}`}
      >
        {copy.chip}
      </span>
      <span className="font-sans text-xs text-outline">{copy.sentence}</span>
    </div>
  );
};
