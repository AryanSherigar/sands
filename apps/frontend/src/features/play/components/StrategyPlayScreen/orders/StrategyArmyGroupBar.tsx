import React from "react";

export interface StrategyArmyGroupBarProps {
  count: number;
  isTargeting: boolean;
  onMove: () => void;
  onHalt: () => void;
  onClear: () => void;
}

const BUTTON_CLASS =
  "rounded-md border border-[#3A3128]/20 bg-[#fff8f4] px-3 py-1 text-xs font-bold text-[#221A12] hover:bg-[#fbebde] cursor-pointer";

export const StrategyArmyGroupBar: React.FC<StrategyArmyGroupBarProps> = ({
  count,
  isTargeting,
  onMove,
  onHalt,
  onClear,
}) => {
  if (count === 0) return null;

  return (
    <div
      role="group"
      aria-label="Army group"
      className="strategy-fade absolute bottom-44 left-1/2 z-30 flex -translate-x-1/2 items-center gap-2 rounded-xl border border-[#3A3128]/20 bg-[#F7F0DC]/95 px-3 py-2 shadow-lg"
    >
      <span className="text-xs font-semibold text-[#221A12]">
        {count} {count === 1 ? "army" : "armies"} grouped
        {isTargeting ? " — choose a destination" : ""}
      </span>
      <button type="button" className={BUTTON_CLASS} onClick={onMove} disabled={isTargeting}>
        Move group
      </button>
      <button type="button" className={BUTTON_CLASS} onClick={onHalt}>
        Halt group
      </button>
      <button type="button" className={BUTTON_CLASS} onClick={onClear}>
        Clear
      </button>
    </div>
  );
};
