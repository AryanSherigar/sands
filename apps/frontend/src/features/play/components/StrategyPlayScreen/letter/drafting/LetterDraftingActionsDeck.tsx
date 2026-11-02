import React, { useState } from "react";
import type { LetterDraftingActionsDeckProps } from "./LetterDraftingStage.types";

const renderActionButtons = (
  isSealing: boolean,
  onDiscard: () => void,
  onSealAndSend: () => void
) => (
  <div className="flex items-center gap-3 w-full md:w-auto justify-end">
    <button
      type="button"
      onClick={onDiscard}
      className="px-3.5 py-2 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
    >
      <span>Discard</span>
      <kbd className="text-[10px] bg-surface-container px-1 py-0.5 rounded text-outline uppercase font-mono">Esc</kbd>
    </button>
    <button
      type="button"
      onClick={onSealAndSend}
      disabled={isSealing}
      className={`group relative overflow-hidden px-5 py-2.5 rounded-lg bg-[#785a00] hover:bg-[#684e00] text-[#ffdf9d] shadow-md transition-all flex items-center gap-2.5 cursor-pointer disabled:cursor-not-allowed active:translate-y-0.5 ${
        isSealing ? "scale-95" : ""
      }`}
    >
      <span className="w-6 h-6 rounded-full bg-[#7c2820] flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
        <span className="material-symbols-outlined text-[16px]">approval</span>
      </span>
      <span className="font-serif text-base tracking-tight font-semibold">Seal and send</span>
      <kbd className="px-1.5 py-0.5 rounded bg-black/25 text-[#ffdf9d] text-[11px] font-mono">Enter</kbd>
    </button>
  </div>
);

const renderReassuranceFooter = () => (
  <div className="flex flex-wrap items-center justify-between pt-2.5 border-t border-on-surface/10 text-xs text-on-surface-variant">
    <div className="flex items-center gap-1.5 font-serif italic">
      <span className="material-symbols-outlined text-[16px] text-meadow-green">lock</span>
      <span>Nothing is sent until you apply the hot seal. The courier waits outside in the courtyard.</span>
    </div>
    <div className="hidden sm:flex items-center gap-3 text-[11px] font-semibold text-on-surface-variant/80">
      <span>[1] Scribe Revision</span>
      <span>[2] Direct Quill</span>
      <span>[Enter] Affix Seal</span>
    </div>
  </div>
);

const renderRewriteInput = (
  hint: string,
  setHint: (val: string) => void,
  handleRewrite: () => void,
  handleKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void
) => (
  <div className="w-full md:w-1/2 flex items-center gap-2 bg-[#efe4c8]/80 px-3.5 py-2.5 rounded-lg shadow-inner border border-outline-variant/30">
    <span className="material-symbols-outlined text-[18px] text-outline">stylus_note</span>
    <input
      aria-label="Draft hint for scribe"
      value={hint}
      onChange={(e) => setHint(e.target.value)}
      onKeyDown={handleKeyDown}
      placeholder='Draft hint: "Make it firmer on the boundary stones"'
      className="w-full bg-transparent border-none text-on-surface text-sm placeholder:text-outline/70 focus:outline-none"
    />
    <button
      type="button"
      onClick={handleRewrite}
      className="px-3.5 py-1.5 rounded bg-[#2e4856] text-white hover:bg-[#3d5a6a] text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors shadow-xs"
    >
      <span className="material-symbols-outlined text-[16px]">refresh</span>
      <span>Rewrite</span>
    </button>
  </div>
);

export const LetterDraftingActionsDeck: React.FC<LetterDraftingActionsDeckProps> = ({
  isSealing,
  onRewrite,
  onDiscard,
  onSealAndSend,
}) => {
  const [hint, setHint] = useState("");
  const handleRewrite = () => {
    if (!hint.trim()) return;
    onRewrite(hint);
    setHint("");
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleRewrite();
  };

  return (
    <footer className="p-4 sm:p-5 rounded-xl bg-parchment-panel/90 backdrop-blur-md shadow-lg border border-[#cfbd94]/60 flex flex-col gap-3.5">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {renderRewriteInput(hint, setHint, handleRewrite, handleKeyDown)}
        {renderActionButtons(isSealing, onDiscard, onSealAndSend)}
      </div>
      {renderReassuranceFooter()}
    </footer>
  );
};
