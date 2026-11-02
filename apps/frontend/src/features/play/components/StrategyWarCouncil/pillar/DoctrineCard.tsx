import type { TacticType } from "../StrategyWarCouncil.types";

export interface DoctrineCardProps {
  tactic: TacticType;
  title: string;
  latinName?: string;
  description: string;
  riskNote?: string;
  prerequisite?: string;
  isSelected: boolean;
  isLocked?: boolean;
  lockReason?: string;
  onSelect: () => void;
}

interface LockedCardProps {
  title: string;
  latinName?: string;
  lockReason?: string;
  description: string;
}

function LockedDoctrineCard({ title, latinName, lockReason, description }: LockedCardProps) {
  return (
    <button
      type="button"
      disabled
      className="doctrine-card locked relative w-full text-left p-2.5 rounded-xl bg-[#f5e5d8]/60 opacity-60 border border-[#3A3128]/10 cursor-not-allowed"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <h3 className="font-serif text-[14px] font-bold text-[#72787c] line-through">{title}</h3>
          {latinName && <span className="text-[11px] italic text-[#72787c]">({latinName})</span>}
        </div>
        <span className="text-[10px] text-[#72787c] flex items-center gap-0.5 font-semibold">
          <span className="material-symbols-outlined text-[14px]">lock</span> Locked
        </span>
      </div>
      <p className="text-[11px] text-[#72787c] leading-tight">{lockReason ?? description}</p>
    </button>
  );
}

function DoctrineStatusBadge({ isSelected }: { isSelected: boolean }) {
  if (isSelected) {
    return (
      <span className="text-[10px] bg-[#46606e] text-white px-1.5 py-0.5 rounded font-bold uppercase tracking-wider flex items-center gap-0.5">
        <span className="material-symbols-outlined text-[12px]">check</span> Active
      </span>
    );
  }
  return <span className="material-symbols-outlined text-[#c2c7cb] text-[16px]">radio_button_unchecked</span>;
}

export function DoctrineCard({
  title,
  latinName,
  description,
  riskNote,
  prerequisite,
  isSelected,
  isLocked = false,
  lockReason,
  onSelect,
}: DoctrineCardProps) {
  if (isLocked) {
    return (
      <LockedDoctrineCard
        title={title}
        latinName={latinName}
        lockReason={lockReason}
        description={description}
      />
    );
  }

  const borderClass = isSelected
    ? "border-2 border-[#46606e] bg-[#f7f0dc]/70 shadow-sm"
    : "border-[#3A3128]/15 bg-[#fff8f4] hover:border-[#3A3128]/35";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`doctrine-card relative w-full text-left p-2.5 rounded-xl shadow-xs transition border ${borderClass} cursor-pointer`}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <h3 className={`font-serif text-[14px] font-bold ${isSelected ? "text-[#46606e]" : "text-[#221a12]"}`}>
            {title}
          </h3>
          {latinName && <span className="text-[11px] italic text-[#6B5E4F]">({latinName})</span>}
        </div>
        <DoctrineStatusBadge isSelected={isSelected} />
      </div>
      <p className="text-[11px] text-[#221a12] leading-tight">{description}</p>
      {prerequisite && <p className="text-[10px] text-[#6B5E4F] mt-1 font-medium">{prerequisite}</p>}
      {riskNote && (
        <div className="mt-1 text-[11px] text-[#a8483e] italic flex items-center gap-1">
          <span className="material-symbols-outlined text-[13px] not-italic">warning</span>
          <span>{riskNote}</span>
        </div>
      )}
    </button>
  );
}
