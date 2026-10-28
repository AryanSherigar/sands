import React, { useState } from "react";
import { IconArrowRight } from "@tabler/icons-react";
import { MONTHS_PER_TURN } from "../../../constants/strategy.constants";
import type { StrategyEndTurnModuleProps } from "./StrategyOrders.types";

function renderUnspentBadge(count: number) {
  if (count <= 0) {
    return null;
  }
  return (
    <div className="px-2.5 py-1.5 rounded-lg bg-[#F7F0DC]/95 border border-[#3A3128]/20 text-[10px] text-[#72787C]">
      <span className="font-bold text-[#221A12]">{count}</span> unspent
    </div>
  );
}

interface ConfirmPromptProps {
  ordersRemaining: number;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmPrompt: React.FC<ConfirmPromptProps> = ({ ordersRemaining, onConfirm, onCancel }) => (
  <div
    role="alertdialog"
    aria-label="Confirm end turn"
    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#F7F0DC]/95 border border-[#3A3128]/20 shadow-lg text-xs text-[#221A12]"
  >
    <span>End the turn with {ordersRemaining} mandates unspent?</span>
    <button
      type="button"
      onClick={onConfirm}
      className="px-2.5 py-1 rounded-lg bg-[#D2A94A] font-bold cursor-pointer"
    >
      End turn
    </button>
    <button
      type="button"
      onClick={onCancel}
      className="px-2.5 py-1 rounded-lg border border-[#3A3128]/20 cursor-pointer"
    >
      Keep planning
    </button>
  </div>
);

export const StrategyEndTurnModule: React.FC<StrategyEndTurnModuleProps> = ({
  ordersRemaining,
  nextSeason,
  isLoading = false,
  isDisabled = false,
  onEndTurn,
}) => {
  const [isConfirming, setIsConfirming] = useState(false);
  const actionText = isLoading ? "Advancing..." : "End Turn";

  const handleEndTurn = () => {
    if (ordersRemaining > 0 && !isConfirming) {
      setIsConfirming(true);
      return;
    }
    setIsConfirming(false);
    onEndTurn();
  };
  const handleCancelConfirm = () => setIsConfirming(false);

  return (
    <div className="fixed bottom-4 right-4 z-40 flex items-center gap-2 pointer-events-auto">
      {isConfirming ? (
        <ConfirmPrompt
          ordersRemaining={ordersRemaining}
          onConfirm={handleEndTurn}
          onCancel={handleCancelConfirm}
        />
      ) : (
        renderUnspentBadge(ordersRemaining)
      )}
      <button
        type="button"
        disabled={isLoading || isDisabled}
        onClick={handleEndTurn}
        className="px-5 py-2.5 rounded-xl bg-[#D2A94A] hover:bg-[#C49B3D] text-[#221A12] font-bold shadow-lg border border-[#3A3128]/20 active:translate-y-0.5 transition-all flex items-center gap-2 disabled:opacity-50 cursor-pointer"
      >
        <div className="flex flex-col text-left leading-tight">
          <span className="font-serif text-base tracking-wide">{actionText}</span>
          {nextSeason ? (
            <span className="text-[9px] uppercase font-bold tracking-wider opacity-85">
              Advances {MONTHS_PER_TURN} mos · {nextSeason}
            </span>
          ) : null}
        </div>
        <IconArrowRight size={16} stroke={2} />
      </button>
    </div>
  );
};
