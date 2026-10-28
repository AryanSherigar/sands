import React, { useState, useMemo } from "react";
import { IconX, IconSearch, IconCheck, IconShieldCheck } from "@tabler/icons-react";
import { BUILTIN_STRATEGY_TRAITS } from "./builtinTraits";
import type { StrategyTrait } from "./StrategyRulerSetup.types";
import type { TraitSelectionDrawerProps } from "./TraitSelectionDrawer.types";

const MIN_TRAITS = 2;
const MAX_TRAITS = 3;

function TraitDrawerHeader({
  selectedCount,
  onClose,
}: {
  selectedCount: number;
  onClose: () => void;
}) {
  const isCountValid = selectedCount >= MIN_TRAITS && selectedCount <= MAX_TRAITS;
  const statusColor = isCountValid ? "text-[#5E8A5A]" : "text-[#7c2820]";

  return (
    <div className="flex items-center justify-between pb-3 border-b border-[#3A3128]/20">
      <div>
        <h3 className="font-serif text-lg font-bold text-[#221a12]">Choose Sovereign Virtues</h3>
        <p className={`text-xs font-medium ${statusColor}`}>
          {selectedCount} of {MAX_TRAITS} selected (Requires {MIN_TRAITS}–{MAX_TRAITS} virtues)
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="p-1 rounded-md text-[#72787c] hover:text-[#221a12] hover:bg-[#3A3128]/10 transition-colors"
        aria-label="Close Virtues Drawer"
      >
        <IconX size={20} />
      </button>
    </div>
  );
}

function TraitListItem({
  trait,
  isSelected,
  canSelect,
  onToggle,
}: {
  trait: StrategyTrait;
  isSelected: boolean;
  canSelect: boolean;
  onToggle: (traitId: string) => void;
}) {
  const cardBorder = isSelected
    ? "border-[#2e4856] bg-white ring-1 ring-[#2e4856]"
    : "border-[#3A3128]/15 bg-white/70 hover:bg-white";

  const handleItemClick = () => {
    if (isSelected || canSelect) {
      onToggle(trait.id);
    }
  };

  return (
    <div
      onClick={handleItemClick}
      className={`p-3 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5 ${cardBorder}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconShieldCheck size={16} className={isSelected ? "text-[#2e4856]" : "text-[#72787c]"} />
          <span className="font-serif text-[15px] font-semibold text-[#221a12]">{trait.name}</span>
        </div>
        <div
          className={`w-5 h-5 rounded flex items-center justify-center border ${
            isSelected
              ? "bg-[#2e4856] text-white border-[#2e4856]"
              : "border-[#72787c]/40 bg-white"
          }`}
        >
          {isSelected && <IconCheck size={14} stroke={3} />}
        </div>
      </div>
      <p className="text-xs text-[#42474b]">{trait.description}</p>
      <div className="flex flex-wrap gap-1 mt-1">
        {trait.effects.map((effect, idx) => (
          <span
            key={`${trait.id}-effect-${idx}`}
            className={`text-[10px] px-1 rounded font-mono ${
              effect.isPositive !== false
                ? "bg-[#5E8A5A]/15 text-[#5E8A5A] font-bold"
                : "bg-[#7c2820]/15 text-[#7c2820]"
            }`}
          >
            {effect.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export const TraitSelectionDrawer: React.FC<TraitSelectionDrawerProps> = ({
  isOpen,
  selectedTraitIds,
  availableTraits,
  onSelectTraits,
  onClose,
}) => {
  const [searchQuery, setSearchQuery] = useState("");

  const allTraits = useMemo(() => {
    const customMap = new Map<string, StrategyTrait>();
    BUILTIN_STRATEGY_TRAITS.forEach((t) => customMap.set(t.id, t));
    availableTraits.forEach((t) => customMap.set(t.id, t));
    return Array.from(customMap.values());
  }, [availableTraits]);

  const filteredTraits = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return allTraits;
    return allTraits.filter(
      (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  }, [allTraits, searchQuery]);

  if (!isOpen) return null;

  const handleToggleTrait = (traitId: string) => {
    if (selectedTraitIds.includes(traitId)) {
      onSelectTraits(selectedTraitIds.filter((id) => id !== traitId));
    } else if (selectedTraitIds.length < MAX_TRAITS) {
      onSelectTraits([...selectedTraitIds, traitId]);
    }
  };

  const hasMaxSelected = selectedTraitIds.length >= MAX_TRAITS;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-md h-full bg-[#F7F0DC] shadow-2xl p-4 flex flex-col gap-3 overflow-hidden border-l border-[#3A3128]/20 animate-fade-in">
        <TraitDrawerHeader selectedCount={selectedTraitIds.length} onClose={onClose} />
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search virtues..."
            className="w-full bg-white/90 text-[#221a12] text-xs pl-8 pr-3 py-2 rounded border border-[#3A3128]/20 focus:outline-none focus:ring-2 focus:ring-[#2e4856]"
          />
          <IconSearch size={14} className="absolute left-2.5 top-2.5 text-[#72787c]" />
        </div>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {filteredTraits.map((trait) => (
            <TraitListItem
              key={trait.id}
              trait={trait}
              isSelected={selectedTraitIds.includes(trait.id)}
              canSelect={!hasMaxSelected}
              onToggle={handleToggleTrait}
            />
          ))}
        </div>
        <button
          type="button"
          onClick={onClose}
          disabled={selectedTraitIds.length < MIN_TRAITS}
          className="w-full py-2.5 rounded bg-[#2e4856] text-white font-serif text-sm font-semibold hover:bg-[#46606e] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
        >
          Confirm Sovereign Virtues ({selectedTraitIds.length}/{MAX_TRAITS})
        </button>
      </div>
    </div>
  );
};
