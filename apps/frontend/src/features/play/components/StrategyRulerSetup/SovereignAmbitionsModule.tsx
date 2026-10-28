import React from "react";
import { IconTarget, IconCheck } from "@tabler/icons-react";
import type { StrategyAmbition } from "./StrategyRulerSetup.types";
import type { SovereignAmbitionsModuleProps } from "./SovereignAmbitionsModule.types";

function AmbitionProgressBar({ progress = 0 }: { progress?: number }) {
  const clampedProgress = Math.max(0, Math.min(100, progress));
  return (
    <div className="w-full bg-[#f0e0d2] rounded-full h-1.5 mt-2 overflow-hidden">
      <div
        className="bg-[#785a00] h-full rounded-full transition-all duration-300"
        style={{ width: `${clampedProgress}%` }}
      />
    </div>
  );
}

function AmbitionCard({ ambition }: { ambition: StrategyAmbition }) {
  return (
    <div className="bg-[#F7F0DC]/90 backdrop-blur-sm p-3 rounded-lg shadow-sm border border-[#785a00]/30 flex items-start gap-2.5">
      <IconTarget size={20} className="text-[#785a00] shrink-0 mt-0.5" />
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-0.5">
          <span className="font-serif text-[15px] font-semibold text-[#221a12]">
            {ambition.name}
          </span>
          <span className="w-4 h-4 rounded-full bg-[#ffdf9d] flex items-center justify-center text-[#775900]">
            <IconCheck size={12} stroke={2.5} />
          </span>
        </div>
        <p className="text-[12px] text-[#42474b] leading-tight">
          {ambition.description}
        </p>
        <AmbitionProgressBar progress={ambition.progress} />
      </div>
    </div>
  );
}

export const SovereignAmbitionsModule: React.FC<SovereignAmbitionsModuleProps> = ({
  activeAmbitions,
  onOpenDrawer,
}) => {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-[#72787c] font-semibold">
          Coronation Ambitions (Choose Victory Path)
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenDrawer}
            className="text-xs text-[#2e4856] font-semibold cursor-pointer hover:underline bg-transparent border-0 p-0"
          >
            Change Ambition
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {activeAmbitions.map((ambition) => (
          <AmbitionCard key={ambition.id} ambition={ambition} />
        ))}
      </div>
    </div>
  );
};
