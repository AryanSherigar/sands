import React from "react";
import { IconShieldCheck, IconAward } from "@tabler/icons-react";
import type { StrategyTrait, StrategyTraitEffect } from "./StrategyRulerSetup.types";
import type { SovereignTraitsModuleProps } from "./SovereignTraitsModule.types";

function TraitEffectChip({ effect }: { effect: StrategyTraitEffect }) {
  const chipClass = effect.isPositive !== false
    ? "bg-[#5E8A5A]/15 text-[#5E8A5A] font-bold"
    : "bg-[#7c2820]/15 text-[#7c2820]";

  return (
    <span className={`text-[11px] px-1.5 py-0.5 rounded font-mono ${chipClass}`}>
      {effect.label}
    </span>
  );
}

function TraitCard({ trait }: { trait: StrategyTrait }) {
  return (
    <div className="bg-[#F7F0DC]/90 backdrop-blur-sm p-3 rounded-lg shadow-sm border border-[#3A3128]/15 flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <IconShieldCheck size={16} className="text-[#2e4856]" />
          <span className="font-serif text-[15px] font-semibold text-[#221a12]">
            {trait.name}
          </span>
        </div>
        <p className="text-[12px] leading-tight text-[#42474b]">
          {trait.description}
        </p>
      </div>
      <div className="mt-2 pt-1.5 flex flex-wrap gap-1 border-t border-[#3A3128]/10">
        {trait.effects.map((effect, idx) => (
          <TraitEffectChip key={`${trait.id}-fx-${idx}`} effect={effect} />
        ))}
      </div>
    </div>
  );
}

export const SovereignTraitsModule: React.FC<SovereignTraitsModuleProps> = ({
  activeTraits,
  maxTraits = 3,
  onOpenDrawer,
}) => {
  const countLabel = `Sovereign Traits (${activeTraits.length} of ${maxTraits} Active)`;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-[#72787c] font-semibold">
          {countLabel}
        </span>
        <button
          type="button"
          onClick={onOpenDrawer}
          className="text-xs text-[#2e4856] font-semibold cursor-pointer hover:underline bg-transparent border-0 p-0"
        >
          Change Virtues
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {activeTraits.map((trait) => (
          <TraitCard key={trait.id} trait={trait} />
        ))}
        {activeTraits.length === 0 && (
          <div className="col-span-3 p-4 text-center text-xs text-[#72787c] italic bg-[#F7F0DC]/50 rounded-lg border border-dashed border-[#72787c]/30">
            <IconAward size={20} className="mx-auto mb-1 opacity-50" />
            No sovereign virtues selected yet. Click &ldquo;Change Virtues&rdquo; to bestow virtues.
          </div>
        )}
      </div>
    </div>
  );
};
