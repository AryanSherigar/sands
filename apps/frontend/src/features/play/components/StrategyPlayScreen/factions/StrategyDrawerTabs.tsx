import React from "react";
import type { StrategyDrawerTabsProps } from "./StrategyDrawerTabs.types";

const TAB_BUTTON_BASE =
  "py-2 px-1 text-[10px] font-bold uppercase tracking-wider [writing-mode:vertical-rl]";

const getTabClass = (isActive: boolean): string =>
  `${TAB_BUTTON_BASE} ${isActive ? "text-[#46606E]" : "text-[#72787C]"}`;

export const StrategyDrawerTabs: React.FC<StrategyDrawerTabsProps> = ({
  activeTab,
  rivalsCount,
  obligationsCount = 0,
  onSelectTab,
}) => {
  const handleFactionsClick = () => onSelectTab(activeTab === "factions" ? null : "factions");
  const handleChronicleClick = () => onSelectTab(activeTab === "chronicle" ? null : "chronicle");
  const handleTreasuryClick = () => onSelectTab(activeTab === "treasury" ? null : "treasury");

  return (
    <div className="flex flex-col gap-2 p-1.5 bg-[#F7F0DC]/95 backdrop-blur-xl border border-r-0 border-[#3A3128]/20 rounded-l-xl shadow-lg">
      <button
        type="button"
        onClick={handleFactionsClick}
        className={getTabClass(activeTab === "factions")}
      >
        <span>Factions ({rivalsCount})</span>
        {obligationsCount > 0 && (
          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-[#A8483E] text-white text-[9px] font-bold">
            {obligationsCount}
          </span>
        )}
      </button>
      <div className="h-px w-full bg-[#3A3128]/10" />
      <button
        type="button"
        onClick={handleChronicleClick}
        className={getTabClass(activeTab === "chronicle")}
      >
        Chronicle
      </button>
      <div className="h-px w-full bg-[#3A3128]/10" />
      <button
        type="button"
        onClick={handleTreasuryClick}
        className={getTabClass(activeTab === "treasury")}
      >
        Treasury
      </button>
    </div>
  );
};
