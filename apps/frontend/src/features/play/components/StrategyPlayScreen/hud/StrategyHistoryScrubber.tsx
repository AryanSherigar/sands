import React from "react";

export interface StrategyHistoryScrubberProps {
  latestTurn: number;
  viewedTurn: number;
  isLoading: boolean;
  hasFailed: boolean;
  onChangeTurn: (turn: number) => void;
  onReturnToPresent: () => void;
}

const BUTTON_CLASS =
  "rounded-md border border-[#3A3128]/20 bg-[#fff8f4] px-2.5 py-1 text-xs font-bold text-[#221A12] hover:bg-[#fbebde] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer";

export const StrategyHistoryScrubber: React.FC<StrategyHistoryScrubberProps> = ({
  latestTurn,
  viewedTurn,
  isLoading,
  hasFailed,
  onChangeTurn,
  onReturnToPresent,
}) => (
  <div
    role="group"
    aria-label="Realm history"
    className="strategy-fade fixed bottom-40 left-1/2 z-40 sm:bottom-auto sm:top-24 flex w-[min(92vw,34rem)] -translate-x-1/2 flex-col gap-1.5 rounded-xl border border-[#3A3128]/20 bg-[#F7F0DC]/95 p-3 shadow-lg"
  >
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs font-semibold text-[#221A12]">
        Turn {viewedTurn} of {latestTurn}
        <span className="ml-2 font-normal italic text-[#72787C]">read only</span>
      </span>
      <button type="button" className={BUTTON_CLASS} onClick={onReturnToPresent}>
        Return to the present
      </button>
    </div>
    <div className="flex items-center gap-2">
      <button type="button" className={BUTTON_CLASS} disabled={viewedTurn <= 0} onClick={() => onChangeTurn(viewedTurn - 1)} aria-label="Earlier turn">
        ‹
      </button>
      <input
        type="range"
        min={0}
        max={latestTurn}
        value={viewedTurn}
        aria-label="Turn"
        onChange={(event) => onChangeTurn(Number(event.target.value))}
        className="w-full accent-[#46606E]"
      />
      <button type="button" className={BUTTON_CLASS} disabled={viewedTurn >= latestTurn} onClick={() => onChangeTurn(viewedTurn + 1)} aria-label="Later turn">
        ›
      </button>
    </div>
    {isLoading ? <span role="status" className="text-[11px] text-[#72787C]">Unrolling the records…</span> : null}
    {hasFailed ? <span role="alert" className="text-[11px] text-[#A8483E]">That turn could not be loaded.</span> : null}
  </div>
);
