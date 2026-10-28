import React, { useEffect } from "react";
import {
  IconGavel,
  IconSun,
  IconAlertTriangle,
  IconLeaf,
  IconCheck,
  IconMoodSad,
  IconMoodSmile,
  IconUser,
} from "@tabler/icons-react";
import type { StrategyEventDialogProps } from "./StrategyEventDialog.types";
import type { EventChoice, StrategyEventPackage } from "../../../types/eventScene.types";

function isChoiceBlocked(eventPackage: StrategyEventPackage, choice: EventChoice): boolean {
  if (eventPackage.queuedChoiceId) return true;
  return choice.isAffordable === false;
}

function formatCost(cost: number): string {
  return `${cost} ${cost === 1 ? "order" : "orders"}`;
}

export const StrategyEventDialog: React.FC<StrategyEventDialogProps> = ({
  isOpen,
  eventPackage,
  onSelectOption,
  onCancelQueued,
  onClose,
}) => {
  useEffect(() => {
    if (!isOpen || !eventPackage) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "Escape" && onClose) {
        e.preventDefault();
        onClose();
        return;
      }

      const num = parseInt(e.key, 10);
      if (!isNaN(num) && num >= 1 && num <= eventPackage.choices.length) {
        const choice = eventPackage.choices[num - 1];
        if (isChoiceBlocked(eventPackage, choice)) return;
        e.preventDefault();
        onSelectOption(choice.id);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, eventPackage, onSelectOption, onClose]);

  if (!isOpen || !eventPackage) return null;

  const isTrouble = eventPackage.category === "trouble";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="strategy-event-title"
        className="relative w-full max-w-[720px] bg-parchment-panel rounded-xl shadow-2xl p-6 border border-on-surface/20 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Decorative Parchment Tint Watermark */}
        <div
          className={`absolute -right-20 -bottom-20 w-72 h-72 rounded-full pointer-events-none blur-2xl ${
            isTrouble ? "bg-tertiary/5" : "bg-meadow-green/10"
          }`}
        />

        {/* Top Wax Seal */}
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center">
          {isTrouble ? (
            <div
              aria-label="Trouble Seal"
              className="relative w-12 h-12 rounded-full bg-gradient-to-br from-[#A8483E] via-[#852E26] to-[#541611] shadow-[0_6px_14px_rgba(124,40,32,0.45)] flex items-center justify-center border border-[#DC7A70]/40 text-surface-bright"
            >
              <IconGavel className="w-6 h-6 text-white drop-shadow" />
            </div>
          ) : (
            <div
              aria-label="Good News Seal"
              className="relative w-12 h-12 rounded-full bg-gradient-to-br from-[#E2B755] via-[#C59B37] to-[#785A00] shadow-[0_6px_14px_rgba(120,90,0,0.4)] flex items-center justify-center border border-[#FED16E]/60 text-surface-bright"
            >
              <IconSun className="w-6 h-6 text-white drop-shadow" />
            </div>
          )}
        </div>

        {/* Header Ribbon with Category & Filigree */}
        <div className="pt-2 pb-3 border-b border-on-surface/15 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isTrouble ? (
                <span className="px-2 py-0.5 rounded bg-tertiary-container text-white font-sans-manrope text-xs tracking-wider uppercase font-bold flex items-center gap-1 shadow-sm">
                  <IconAlertTriangle className="w-3.5 h-3.5" />
                  Trouble
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-meadow-green text-white font-sans-manrope text-xs tracking-wider uppercase font-bold flex items-center gap-1 shadow-sm">
                  <IconLeaf className="w-3.5 h-3.5" />
                  Good News
                </span>
              )}
              <span className="font-sans-manrope text-xs text-outline">
                Decreed under royal seal
              </span>
            </div>
            {eventPackage.turnText && (
              <span className="font-sans-manrope text-xs text-on-surface-variant">
                {eventPackage.turnText}
              </span>
            )}
          </div>
          <h2
            id="strategy-event-title"
            className={`mt-2 font-serif-garamond text-2xl font-bold leading-tight ${
              isTrouble ? "text-tertiary" : "text-on-surface"
            }`}
          >
            {eventPackage.title}
          </h2>
          {eventPackage.subheading && (
            <p className="font-sans-manrope text-xs text-on-surface-variant mt-0.5">
              {eventPackage.subheading}
            </p>
          )}
        </div>

        {/* Character & Vignette Section */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-parchment-base/90 border border-on-surface/10 shadow-sm mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`relative w-12 h-12 rounded-full overflow-hidden border-2 shadow-sm flex-shrink-0 bg-surface-dim flex items-center justify-center ${
                isTrouble ? "border-tertiary" : "border-meadow-green"
              }`}
            >
              {eventPackage.character.avatarUrl ? (
                <img
                  src={eventPackage.character.avatarUrl}
                  alt={eventPackage.character.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <IconUser className="w-6 h-6 text-on-surface/50" />
              )}
            </div>
            <div className="min-w-0">
              <div className="font-serif-garamond text-lg font-bold text-on-surface truncate leading-tight">
                {eventPackage.character.name}
              </div>
              <div className="font-sans-manrope text-xs text-on-surface-variant truncate">
                {eventPackage.character.title}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-sans-manrope pl-3 border-l border-on-surface/10 flex-shrink-0">
            <span className="text-on-surface-variant">Disposition:</span>
            <span
              className={`px-2 py-0.5 rounded font-bold flex items-center gap-1 ${
                isTrouble
                  ? "bg-tertiary/15 text-tertiary"
                  : "bg-meadow-green/15 text-meadow-green"
              }`}
            >
              {isTrouble ? (
                <IconMoodSad className="w-3.5 h-3.5" />
              ) : (
                <IconMoodSmile className="w-3.5 h-3.5" />
              )}
              {eventPackage.character.disposition}
            </span>
          </div>
        </div>

        {/* Narrative Text & Causal Attribution */}
        <div className="mb-4 space-y-2 p-3.5 rounded-lg bg-surface-container-high/40 border border-on-surface/10">
          <p className="font-sans-manrope text-sm text-on-surface leading-relaxed">
            {eventPackage.bodyProse}
          </p>
          {eventPackage.causeQuote && (
            <p
              className={`font-sans-manrope text-xs italic ${
                isTrouble ? "text-tertiary" : "text-meadow-green"
              }`}
            >
              {eventPackage.causeQuote}
            </p>
          )}
        </div>

        {eventPackage.queuedChoiceId && (
          <div
            role="status"
            className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-meadow-green/40 bg-meadow-green/10 px-3 py-2 font-sans-manrope text-xs text-on-surface"
          >
            <span>
              Answer queued:{" "}
              <strong>
                {eventPackage.choices.find((c) => c.id === eventPackage.queuedChoiceId)?.label ??
                  eventPackage.queuedChoiceId}
              </strong>
              . It takes effect when the turn ends.
            </span>
            {eventPackage.queuedCommandId && onCancelQueued && (
              <button
                type="button"
                onClick={() => onCancelQueued(eventPackage.queuedCommandId as string)}
                className="rounded border border-on-surface/20 px-2 py-1 font-semibold hover:bg-black/5"
              >
                Cancel answer
              </button>
            )}
          </div>
        )}

        {/* Stacked Decision Buttons */}
        <div className="flex flex-col gap-2">
          {eventPackage.choices.map((choice, index) => {
            const shortcutNum = index + 1;
            const isPrimary = index === 0;
            const isQueued = eventPackage.queuedChoiceId === choice.id;
            const isBlocked = isChoiceBlocked(eventPackage, choice);
            return (
              <button
                key={choice.id}
                type="button"
                disabled={isBlocked}
                aria-disabled={isBlocked}
                onClick={() => onSelectOption(choice.id)}
                className={`group w-full text-left p-3 rounded-lg transition-all duration-150 shadow-sm flex items-start justify-between gap-3 active:translate-y-[1px] disabled:cursor-not-allowed ${
                  isBlocked && !isQueued ? "opacity-50" : ""
                } ${
                  isPrimary
                    ? `${isTrouble ? "bg-tertiary" : "bg-meadow-green"} text-white hover:bg-primary-container-wilds`
                    : "bg-parchment-base hover:bg-secondary-container-wilds/40 text-on-surface border border-on-surface/15"
                }`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  <span
                    className={`flex-shrink-0 w-6 h-6 rounded flex items-center justify-center font-sans-manrope text-xs font-bold ${
                      isPrimary
                        ? "bg-white/20 text-white"
                        : "bg-on-surface/10 text-on-surface"
                    }`}
                  >
                    {shortcutNum}
                  </span>
                  <div className="min-w-0">
                    <div className="font-sans-manrope text-sm font-semibold leading-snug flex items-center gap-2">
                      <span>{choice.label}</span>
                      {choice.orderCost !== undefined && (
                        <span className="px-1.5 py-0.5 rounded bg-black/10 text-[10px] font-sans-manrope uppercase tracking-wider font-bold">
                          {formatCost(choice.orderCost)}
                        </span>
                      )}
                      {isQueued && (
                        <span className="px-1.5 py-0.5 rounded bg-meadow-green text-white text-[10px] font-sans-manrope uppercase tracking-wider font-bold">
                          Queued
                        </span>
                      )}
                      {choice.isAffordable === false && !isQueued && (
                        <span className="px-1.5 py-0.5 rounded bg-tertiary text-white text-[10px] font-sans-manrope uppercase tracking-wider font-bold">
                          Can't afford
                        </span>
                      )}
                      {choice.isMapOrder && (
                        <span className="px-1.5 py-0.2 rounded bg-tertiary-fixed text-on-tertiary-fixed-variant text-[10px] font-sans-manrope uppercase tracking-wider font-bold">
                          Map Order
                        </span>
                      )}
                    </div>
                    {choice.effects && choice.effects.length > 0 && (
                      <div
                        className={`mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-sans-manrope text-xs ${
                          isPrimary ? "text-white/80" : "text-on-surface-variant"
                        }`}
                      >
                        {choice.effects.map((effect, effIdx) => (
                          <React.Fragment key={effIdx}>
                            {effIdx > 0 && <span>•</span>}
                            <span>{effect}</span>
                          </React.Fragment>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <IconCheck
                  className={`w-5 h-5 flex-shrink-0 mt-0.5 transition-transform group-hover:scale-110 ${
                    isPrimary
                      ? "text-white/70 group-hover:text-white"
                      : "text-on-surface-variant group-hover:text-on-surface"
                  }`}
                />
              </button>
            );
          })}
        </div>

        {eventPackage.neglectWarning && (
          <p className="mt-3 font-sans-manrope text-xs text-tertiary">
            If you leave this unanswered: {eventPackage.neglectWarning}
          </p>
        )}

        {/* Footer Micro-Metadata */}
        <div className="mt-4 pt-2 border-t border-on-surface/10 flex items-center justify-between font-sans-manrope text-xs text-on-surface-variant">
          <span>
            Press{" "}
            {eventPackage.choices.map((_, i) => (
              <React.Fragment key={i}>
                {i > 0 && (i === eventPackage.choices.length - 1 ? " or " : ", ")}
                <kbd className="px-1.5 py-0.5 bg-black/5 rounded border border-on-surface/20 text-on-surface font-mono font-bold">
                  {i + 1}
                </kbd>
              </React.Fragment>
            ))}
          </span>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="hover:underline text-on-surface-variant text-xs cursor-pointer"
            >
              Close [Esc]
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
