import React from "react";
import type { LetterDraftingStageProps } from "./LetterDraftingStage.types";
import { LetterArchivalReference } from "./LetterArchivalReference";
import { LetterScribeInstructionBar } from "./LetterScribeInstructionBar";
import { LetterParchmentCanvas } from "./LetterParchmentCanvas";
import { LetterDraftingActionsDeck } from "./LetterDraftingActionsDeck";
import { LetterStillLifeAccents } from "./LetterStillLifeAccents";

const renderDraftingHeader = (onDiscard: () => void) => (
  <header className="relative z-10 flex flex-wrap items-center justify-between gap-3 bg-parchment-panel/85 backdrop-blur-md px-4 py-2 rounded-lg shadow-sm border border-[#cfbd94]/60">
    <div className="flex items-center gap-3 sm:gap-4">
      <button
        type="button"
        onClick={onDiscard}
        className="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container/80 hover:bg-surface-container-high text-[#2e4856] hover:text-[#182a34] font-serif text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-[#2e4856] cursor-pointer border border-[#cfbd94]/50 shadow-xs"
      >
        <span className="material-symbols-outlined text-[18px] text-[#2e4856]">arrow_back</span>
        <span>Return to Desk</span>
        <kbd className="px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface-variant text-[10px] uppercase font-mono font-bold">
          Esc
        </kbd>
      </button>
      <div className="h-4 w-[1px] bg-outline-variant/60" />
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-tertiary text-[20px]">history_edu</span>
        <h1 className="font-serif text-base sm:text-lg font-bold text-on-surface tracking-tight">
          Drafting Courier Missive
        </h1>
      </div>
    </div>
    <div className="flex items-center gap-2 bg-surface-container-lowest/80 px-3 py-1 rounded-full shadow-inner border border-[#cfbd94]/30">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary" />
      </span>
      <span className="text-xs text-on-surface-variant flex items-center gap-1.5">
        <span className="material-symbols-outlined text-[16px] text-secondary">graphic_eq</span>
        <span>Soft tallow crackle &amp; quiet scratching of steel nib on linen rag</span>
      </span>
    </div>
  </header>
);

export const LetterDraftingStage: React.FC<LetterDraftingStageProps> = (props) => {
  const { pkg, activeDraft, mode, canUndo, canRedo, isSealing } = props;
  const { onRewrite, onUpdateBody, onUndo, onRedo, onDiscard, onSealAndSend } = props;

  return (
    <div className="relative w-full flex flex-col items-center">
      <div className="relative w-full overflow-hidden rounded-2xl bg-app-bg text-on-surface shadow-2xl p-4 sm:p-6 md:p-8 flex flex-col gap-4 border border-[#c9b78e]/70">
        <div className="absolute inset-0 pointer-events-none opacity-40 bg-[radial-gradient(ellipse_at_70%_20%,_#F7F0DC_0%,_transparent_60%),radial-gradient(circle_at_15%_85%,_#DCE7EA_0%,_transparent_55%)]" />
        <div className="absolute -right-24 -top-24 w-96 h-96 rounded-full bg-secondary/10 blur-3xl pointer-events-none" />
        <div className="absolute -left-20 top-1/2 w-80 h-80 rounded-full bg-sky-mist/30 blur-3xl pointer-events-none" />
        <LetterStillLifeAccents />

        {renderDraftingHeader(onDiscard)}

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <LetterArchivalReference incoming={pkg.incoming} provenance={pkg.provenance} />
          <main className="lg:col-span-8 flex flex-col gap-3.5">
            <LetterScribeInstructionBar
              scribe={pkg.scribe}
              instruction={activeDraft.instruction}
              revisionIndex={activeDraft.revisionIndex}
              canUndo={canUndo}
              canRedo={canRedo}
              onUndo={onUndo}
              onRedo={onRedo}
            />
            <LetterParchmentCanvas
              draft={activeDraft}
              isDirectQuill={mode === "direct_quill"}
              onUpdateBody={onUpdateBody}
            />
            <LetterDraftingActionsDeck
              isSealing={isSealing}
              onRewrite={onRewrite}
              onDiscard={onDiscard}
              onSealAndSend={onSealAndSend}
            />
          </main>
        </div>
      </div>
    </div>
  );
};
