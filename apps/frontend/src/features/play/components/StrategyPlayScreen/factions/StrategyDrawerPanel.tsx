import React from "react";
import { IconPin } from "@tabler/icons-react";
import { KnownFactionsLedger } from "./KnownFactionsLedger";
import { LiveChronicleFeed } from "./LiveChronicleFeed";
import { TreasuryDrawerPanel } from "./TreasuryDrawerPanel";
import type { StrategyDrawerPanelProps } from "./StrategyDrawerPanel.types";

function renderDrawerContent(props: StrategyDrawerPanelProps): React.ReactNode {
  const { activeTab, world, onSubmitOrder, playthroughId, onJumpToRegion, rivals, diplomacy } =
    props;
  if (activeTab === "treasury" && world && onSubmitOrder) {
    return <TreasuryDrawerPanel world={world} onSubmitOrder={onSubmitOrder} />;
  }
  if (activeTab === "chronicle") {
    return <LiveChronicleFeed playthroughId={playthroughId} onJumpToRegion={onJumpToRegion} />;
  }
  return (
    <KnownFactionsLedger
      rivals={rivals}
      diplomacy={diplomacy}
      world={world}
      onSubmitOrder={onSubmitOrder}
    />
  );
}

export const StrategyDrawerPanel: React.FC<StrategyDrawerPanelProps> = (props) => {
  const { isOpen, isPinned, activeTab, onTogglePin } = props;
  const pinClass = `text-xs px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer transition-colors ${
    isPinned ? "bg-[#46606E] text-white" : "text-[#72787C] hover:text-[#221A12]"
  }`;
  const widthClass = isOpen ? "w-[340px]" : "w-0";
  const panelTitle = activeTab === "treasury" ? "Royal Exchequer" : "Realm Intelligence";

  return (
    <div
      className={`transition-all duration-300 ease-out overflow-hidden h-[75vh] bg-[#F7F0DC]/95 backdrop-blur-xl border border-r-0 border-[#3A3128]/20 rounded-l-xl shadow-2xl flex flex-col ${widthClass}`}
    >
      <div className="flex items-center justify-between p-2 border-b border-[#72787C]/20">
        <span className="text-xs font-bold text-[#221A12]">{panelTitle}</span>
        <button type="button" onClick={onTogglePin} className={pinClass}>
          <IconPin size={12} stroke={1.75} />
          <span>Pin</span>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">{renderDrawerContent(props)}</div>
    </div>
  );
};
