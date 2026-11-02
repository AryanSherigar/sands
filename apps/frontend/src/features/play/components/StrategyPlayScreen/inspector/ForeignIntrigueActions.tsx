import React from "react";
import type { StrategyInspectorAction } from "../../../types/strategyActions.types";

export interface ForeignIntrigueActionsProps {
  regionId: string;
  ownerId: string;
  onAction?: (action: StrategyInspectorAction) => void;
}

const BUTTON_CLASS =
  "py-1.5 px-2 rounded bg-[#F5E5D8] border border-[#3A3128]/15 text-[#221A12] text-xs font-bold hover:bg-[#F0E0D2] cursor-pointer";

export const ForeignIntrigueActions: React.FC<ForeignIntrigueActionsProps> = ({
  regionId,
  ownerId,
  onAction,
}) => (
  <div className="grid grid-cols-2 gap-2 border-t border-[#72787C]/30 p-3">
    <button type="button" className={BUTTON_CLASS} onClick={() => onAction?.({ type: "map_scout", regionId })}>
      Scout province
    </button>
    <button
      type="button"
      className={BUTTON_CLASS}
      onClick={() => onAction?.({ type: "fabricate_claim", targetFactionId: ownerId, regionId })}
    >
      Fabricate claim
    </button>
  </div>
);
