import React from "react";
import { calculateExchangeDots } from "../utils/negotiationStance.utils";
import type { NegotiationHeaderProps } from "./NegotiationHeader.types";

export const NegotiationHeader: React.FC<NegotiationHeaderProps> = ({
  title,
  exchangesRemaining,
  totalExchanges = 6,
  isFinished = false,
  onExit,
  onToggleChronicles,
}) => {
  const { usedCount, totalCap, activeDots } = calculateExchangeDots(
    exchangesRemaining,
    totalExchanges
  );
  const canExit = isFinished;

  return (
    <header className="w-full h-14 bg-parchment-panel/90 backdrop-blur-md px-8 flex items-center justify-between shadow-sm relative z-30 border-b border-outline-variant/30">
      <button
        type="button"
        disabled={!canExit}
        onClick={onExit}
        className="group flex items-center gap-2 text-on-surface hover:text-primary transition-colors cursor-pointer py-1 px-2.5 rounded-lg hover:bg-surface-variant/40 disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Exit to Encampment"
        title={canExit ? undefined : "Break talks to leave the table"}
      >
        <span className="material-symbols-outlined text-[18px] transition-transform group-hover:-translate-x-1">
          arrow_left_alt
        </span>
        <span className="font-sans text-sm tracking-wider">Exit to Encampment</span>
      </button>

      <div className="flex items-center gap-3">
        <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
        <h1 className="font-serif text-xl font-semibold text-on-surface tracking-wide">
          {title}
        </h1>
        <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 bg-surface-container/70 px-3.5 py-1 rounded-full shadow-inner border border-outline-variant/30">
          <span className="font-sans text-xs uppercase tracking-wider text-outline">
            Exchanges Left
          </span>
          <div className="flex items-center gap-1.5" aria-hidden="true">
            {activeDots.map((isActive, index) => (
              <span
                key={index}
                className={`w-2 h-2 rounded-full transition-colors ${
                  isActive ? "bg-primary" : "bg-outline-variant"
                }`}
              />
            ))}
          </div>
          <span className="font-stat-numeric text-xs font-semibold text-primary ml-1">
            {usedCount} of {totalCap}
          </span>
        </div>

        {onToggleChronicles ? (
          <button
            type="button"
            onClick={onToggleChronicles}
            className="p-1.5 rounded-lg text-primary hover:bg-surface-variant/50 transition-colors cursor-pointer"
            title="View Chronicles"
          >
            <span className="material-symbols-outlined text-[20px]">menu_book</span>
          </button>
        ) : null}
      </div>
    </header>
  );
};
