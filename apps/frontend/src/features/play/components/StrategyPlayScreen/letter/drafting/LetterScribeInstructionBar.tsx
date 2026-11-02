import React from "react";
import type { LetterScribeInstructionBarProps } from "./LetterDraftingStage.types";

const renderRevisionControls = (
  revisionIndex: number,
  canUndo: boolean,
  canRedo: boolean,
  onUndo: () => void,
  onRedo: () => void
) => (
  <div className="flex items-center gap-2 ml-auto">
    <button
      type="button"
      className="hidden sm:flex items-center gap-1 text-[#2e4856] hover:text-on-surface text-xs font-semibold px-2 py-1 rounded transition-colors cursor-pointer"
    >
      <span className="material-symbols-outlined text-[16px]">edit_note</span>
      <span>Edit instruction</span>
    </button>
    <div className="hidden sm:block h-4 w-[1px] bg-outline-variant/60" />
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={onUndo}
        disabled={!canUndo}
        aria-label="Undo draft change"
        className="p-1 rounded hover:bg-surface-container disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors text-on-surface-variant"
      >
        <span className="material-symbols-outlined text-[18px]">undo</span>
      </button>
      <button
        type="button"
        onClick={onRedo}
        disabled={!canRedo}
        aria-label="Redo draft change"
        className="p-1 rounded hover:bg-surface-container disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors text-on-surface-variant"
      >
        <span className="material-symbols-outlined text-[18px]">redo</span>
      </button>
    </div>
    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant border border-outline-variant/30">
      Draft Rev. {revisionIndex}
    </span>
  </div>
);

export const LetterScribeInstructionBar: React.FC<LetterScribeInstructionBarProps> = (props) => {
  const { scribe, instruction, revisionIndex, canUndo, canRedo, onUndo, onRedo } = props;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-parchment-panel/90 backdrop-blur-md shadow-sm border border-[#cfbd94]/60">
      <div className="flex items-center gap-3 min-w-0">
        <div className="relative w-10 h-10 rounded-full overflow-hidden shadow-inner bg-surface-container flex-shrink-0 border border-secondary/30">
          {scribe.avatarUrl ? (
            <img src={scribe.avatarUrl} alt={scribe.name} className="w-full h-full object-cover" />
          ) : null}
        </div>
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-on-surface">{scribe.name}</span>
            <span className="text-xs text-on-surface-variant">({scribe.title})</span>
          </div>
          <p className="font-serif text-sm text-[#2e4856] italic truncate">“{instruction}”</p>
        </div>
      </div>
      {renderRevisionControls(revisionIndex, canUndo, canRedo, onUndo, onRedo)}
    </div>
  );
};
