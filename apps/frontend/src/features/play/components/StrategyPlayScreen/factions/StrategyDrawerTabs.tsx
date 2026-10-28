import React from "react";
import type { StrategyDrawerTabsProps } from "./StrategyDrawerTabs.types";

const TAB_BUTTON_BASE =
  "py-2 px-1 text-[10px] font-bold uppercase tracking-wider [writing-mode:vertical-rl]";

export const StrategyDrawerTabs: React.FC<StrategyDrawerTabsProps> = ({
  activeTab,
  rivalsCount,
  onSelectTab,
}) => {
  const handleFactionsClick = () => {
    onSelectTab(activeTab === "factions" ? null : "factions");
  };

  const handleChronicleClick = () => {
    onSelectTab(activeTab === "chronicle" ? null : "chronicle");
  };

  const factionsClass = `${TAB_BUTTON_BASE} ${
    activeTab === "factions" ? "text-[#46606E]" : "text-[#72787C]"
  }`;
  const chronicleClass = `${TAB_BUTTON_BASE} ${
    activeTab === "chronicle" ? "text-[#46606E]" : "text-[#72787C]"
  }`;

  return (
    <div className="flex flex-col gap-2 p-1.5 bg-[#F7F0DC]/95 backdrop-blur-xl border border-r-0 border-[#3A3128]/20 rounded-l-xl shadow-lg">
      <button type="button" onClick={handleFactionsClick} className={factionsClass}>
        Factions ({rivalsCount})
      </button>
      <div className="h-px w-full bg-[#3A3128]/10" />
      <button type="button" onClick={handleChronicleClick} className={chronicleClass}>
        Chronicle
      </button>
    </div>
  );
};
