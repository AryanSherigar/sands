import React, { useMemo } from "react";
import { IconX, IconCheck, IconTarget } from "@tabler/icons-react";
import { BUILTIN_STRATEGY_AMBITIONS } from "./builtinAmbitions";
import type { StrategyAmbition } from "./StrategyRulerSetup.types";
import type { AmbitionSelectionDrawerProps } from "./AmbitionSelectionDrawer.types";

const MIN_AMBITIONS = 1;
const MAX_AMBITIONS = 2;

function AmbitionDrawerHeader({
  selectedCount,
  onClose,
}: {
  selectedCount: number;
  onClose: () => void;
}) {
  const isCountValid = selectedCount >= MIN_AMBITIONS && selectedCount <= MAX_AMBITIONS;
  const statusColor = isCountValid ? "text-[#5E8A5A]" : "text-[#7c2820]";

  return (
    <div className="flex items-center justify-between pb-3 border-b border-[#3A3128]/20">
      <div>
        <h3 className="font-serif text-lg font-bold text-[#221a12]">Choose Coronation Ambitions</h3>
        <p className={`text-xs font-medium ${statusColor}`}>
          {selectedCount} of {MAX_AMBITIONS} selected (Requires {MIN_AMBITIONS}–{MAX_AMBITIONS} ambitions)
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="p-1 rounded-md text-[#72787c] hover:text-[#221a12] hover:bg-[#3A3128]/10 transition-colors"
        aria-label="Close Ambitions Drawer"
      >
        <IconX size={20} />
      </button>
    </div>
  );
}

function AmbitionListItem({
  ambition,
  isSelected,
  canSelect,
  onToggle,
}: {
  ambition: StrategyAmbition;
  isSelected: boolean;
  canSelect: boolean;
  onToggle: (ambitionId: string) => void;
}) {
  const cardBorder = isSelected
    ? "border-[#785a00] bg-white ring-1 ring-[#785a00]"
    : "border-[#3A3128]/15 bg-white/70 hover:bg-white";

  const handleItemClick = () => {
    if (isSelected || canSelect) {
      onToggle(ambition.id);
    }
  };

  return (
    <div
      onClick={handleItemClick}
      className={`p-3 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5 ${cardBorder}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconTarget size={18} className={isSelected ? "text-[#785a00]" : "text-[#72787c]"} />
          <span className="font-serif text-[15px] font-semibold text-[#221a12]">{ambition.name}</span>
        </div>
        <div
          className={`w-5 h-5 rounded flex items-center justify-center border ${
            isSelected
              ? "bg-[#785a00] text-white border-[#785a00]"
              : "border-[#72787c]/40 bg-white"
          }`}
        >
          {isSelected && <IconCheck size={14} stroke={3} />}
        </div>
      </div>
      <p className="text-xs text-[#42474b]">{ambition.description}</p>
    </div>
  );
}

export const AmbitionSelectionDrawer: React.FC<AmbitionSelectionDrawerProps> = ({
  isOpen,
  selectedAmbitionIds,
  availableAmbitions,
  onSelectAmbitions,
  onClose,
}) => {
  const allAmbitions = useMemo(() => {
    const customMap = new Map<string, StrategyAmbition>();
    BUILTIN_STRATEGY_AMBITIONS.forEach((a) => customMap.set(a.id, a));
    availableAmbitions.forEach((a) => customMap.set(a.id, a));
    return Array.from(customMap.values());
  }, [availableAmbitions]);

  if (!isOpen) return null;

  const handleToggleAmbition = (ambitionId: string) => {
    if (selectedAmbitionIds.includes(ambitionId)) {
      onSelectAmbitions(selectedAmbitionIds.filter((id) => id !== ambitionId));
    } else if (selectedAmbitionIds.length < MAX_AMBITIONS) {
      onSelectAmbitions([...selectedAmbitionIds, ambitionId]);
    }
  };

  const hasMaxSelected = selectedAmbitionIds.length >= MAX_AMBITIONS;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-md h-full bg-[#F7F0DC] shadow-2xl p-4 flex flex-col gap-3 overflow-hidden border-l border-[#3A3128]/20 animate-fade-in">
        <AmbitionDrawerHeader selectedCount={selectedAmbitionIds.length} onClose={onClose} />
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {allAmbitions.map((ambition) => (
            <AmbitionListItem
              key={ambition.id}
              ambition={ambition}
              isSelected={selectedAmbitionIds.includes(ambition.id)}
              canSelect={!hasMaxSelected}
              onToggle={handleToggleAmbition}
            />
          ))}
        </div>
        <button
          type="button"
          onClick={onClose}
          disabled={selectedAmbitionIds.length < MIN_AMBITIONS}
          className="w-full py-2.5 rounded bg-[#785a00] text-white font-serif text-sm font-semibold hover:bg-[#967000] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
        >
          Confirm Ambitions ({selectedAmbitionIds.length}/{MAX_AMBITIONS})
        </button>
      </div>
    </div>
  );
};
