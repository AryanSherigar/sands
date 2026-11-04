import React, { useState } from "react";
import { ClauseBuilderDialog } from "./ClauseBuilderDialog";
import type { NegotiationConsoleProps } from "./NegotiationConsole.types";

export const NegotiationConsole: React.FC<NegotiationConsoleProps> = ({
  regions = [],
  isDisabled = false,
  hasPendingProposal = false,
  isDrawerOpen = false,
  isDeclinable = true,
  isTreatyAvailable = true,
  onSend,
  onToggleDrawer,
  onBreakTalks,
}) => {
  const [text, setText] = useState("");
  const [isConfirmBreakOpen, setIsConfirmBreakOpen] = useState(false);
  const [isClauseBuilderOpen, setIsClauseBuilderOpen] = useState(false);
  const trimmed = text.trim();
  const canSend = !isDisabled && trimmed.length > 0;

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!canSend) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <footer className="w-full bg-parchment-panel/95 backdrop-blur-md px-10 py-5 shadow-2xl relative z-20 border-t border-outline-variant/30">
      <div className="max-w-4xl mx-auto space-y-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-3">
          <div className="flex-1 relative flex items-center bg-surface-container-low rounded-xl shadow-inner px-4 py-2.5 focus-within:bg-surface-container-lowest transition-all border border-outline-variant/30">
            <span className="material-symbols-outlined text-outline mr-2 text-[20px]">
              ink_pen
            </span>
            <input
              type="text"
              id="negotiation-speech-input"
              name="speech"
              disabled={isDisabled}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Speak to the ruler, negotiate terms, or state your intent..."
              className="w-full bg-transparent border-0 outline-none text-on-surface font-sans text-base placeholder:text-outline placeholder:font-sans placeholder:text-sm disabled:opacity-40"
            />
          </div>

          <button
            type="submit"
            disabled={!canSend}
            className="px-5 py-2.5 bg-secondary-container text-on-secondary-container hover:bg-secondary-fixed transition-all rounded-xl shadow-md font-sans text-sm font-semibold flex items-center gap-2 cursor-pointer active:translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Speak"
          >
            <span>Speak</span>
            <span className="material-symbols-outlined text-[18px]">send</span>
          </button>

          {isTreatyAvailable ? (
          <button
            type="button"
            onClick={onToggleDrawer}
            className={`relative p-2.5 bg-surface-container hover:bg-surface-variant text-primary rounded-xl shadow-sm transition-all cursor-pointer border border-outline-variant/30 ${
              isDrawerOpen ? "ring-2 ring-primary" : ""
            }`}
            title="Toggle 'On the Table' Treaty Drawer"
            aria-label="Toggle Treaty Drawer"
          >
            <span className="material-symbols-outlined text-[24px]">history_edu</span>
            {hasPendingProposal ? (
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-secondary rounded-full ring-2 ring-parchment-panel animate-pulse" />
            ) : null}
          </button>
          ) : null}
        </form>

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <span className="px-3.5 py-1 rounded-full bg-primary text-on-primary font-sans text-xs font-semibold shadow-sm">
              Say
            </span>

            {isTreatyAvailable ? (
              <>
            <button
              type="button"
              onClick={onToggleDrawer}
              className="px-3.5 py-1 rounded-full bg-surface-container-high text-on-surface hover:bg-surface-variant font-sans text-xs font-semibold transition-all cursor-pointer border border-outline-variant/30"
            >
              Offer
            </button>

            <button
              type="button"
              disabled={isDisabled}
              onClick={() => setIsClauseBuilderOpen(true)}
              className="px-3.5 py-1 rounded-full bg-surface-container-high text-on-surface hover:bg-surface-variant font-sans text-xs font-semibold transition-all cursor-pointer border border-outline-variant/30 disabled:opacity-40"
            >
              Draft a clause
            </button>
              </>
            ) : null}

            {isDeclinable ? (
              <button
                type="button"
                disabled={isDisabled}
                onClick={() => setIsConfirmBreakOpen(true)}
                className="px-3.5 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant hover:bg-tertiary-container hover:text-on-tertiary font-sans text-xs font-semibold transition-all cursor-pointer disabled:opacity-40 border border-tertiary/30"
              >
                Break Talks
              </button>
            ) : null}
          </div>

          <span className="font-sans text-xs text-outline italic">
            Press <kbd className="px-1.5 py-0.5 bg-surface-container rounded shadow-inner text-on-surface font-stat-numeric">Enter ↵</kbd> to state proposal
          </span>
        </div>
      </div>

      {isClauseBuilderOpen ? (
        <ClauseBuilderDialog
          regions={regions}
          onUse={(sentence) => {
            setText(sentence);
            setIsClauseBuilderOpen(false);
          }}
          onCancel={() => setIsClauseBuilderOpen(false)}
        />
      ) : null}
      {isConfirmBreakOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 backdrop-blur-xs p-4">
          <div className="bg-parchment-panel p-6 rounded-2xl shadow-2xl max-w-md w-full border border-tertiary/40 space-y-4">
            <div className="flex items-center gap-2 text-tertiary font-serif text-lg font-semibold">
              <span className="material-symbols-outlined">warning</span>
              <span>Break Off Negotiations</span>
            </div>
            <p className="font-sans text-sm text-on-surface leading-relaxed">
              Are you sure you want to walk away from talks? The rival leader will remember this slight and no treaty will be ratified.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsConfirmBreakOpen(false)}
                className="px-4 py-2 rounded-xl font-sans text-xs font-semibold bg-surface-container hover:bg-surface-variant cursor-pointer"
              >
                Continue Talks
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsConfirmBreakOpen(false);
                  onBreakTalks();
                }}
                className="px-4 py-2 rounded-xl font-sans text-xs font-semibold bg-tertiary text-on-tertiary hover:bg-tertiary-container cursor-pointer shadow-md"
              >
                Confirm Break Talks
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </footer>
  );
};
