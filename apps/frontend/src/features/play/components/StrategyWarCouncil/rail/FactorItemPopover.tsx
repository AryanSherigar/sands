import type { TacticalFactor } from "../StrategyWarCouncil.types";

export function FactorItemPopover({ factor }: { factor: TacticalFactor }) {
  return (
    <div className="group relative flex items-center justify-between p-1.5 rounded bg-[#fff8f4]/60 hover:bg-[#fff8f4] border border-transparent hover:border-[#3A3128]/15 transition cursor-pointer">
      <div className="flex items-center gap-1.5 min-w-0">
        <span className={`material-symbols-outlined text-[16px] ${factor.isPositive ? "text-[#5E8A5A]" : "text-[#7c2820]"}`}>
          {factor.icon}
        </span>
        <span className="text-[12px] truncate text-[#221a12] font-medium">{factor.name}</span>
      </div>
      <span className={`text-[12px] font-semibold ${factor.isPositive ? "text-[#5E8A5A]" : "text-[#7c2820]"}`}>
        {factor.isPositive ? `+${factor.valuePercent}%` : `${factor.valuePercent}%`}
      </span>
      {/* Arithmetic Tooltip */}
      <div className="absolute left-full ml-2 top-0 w-64 p-2.5 bg-[#F7F0DC] text-[#221a12] rounded-lg shadow-xl hidden group-hover:block z-50 border border-[#3A3128]/15 pointer-events-none">
        <div className="font-semibold text-[#2e4856] text-[12px] mb-1 flex items-center gap-1">
          <span className="material-symbols-outlined text-[15px]">calculate</span>
          <span>{factor.title}</span>
        </div>
        <p className="text-[11px] leading-snug">{factor.explanation}</p>
      </div>
    </div>
  );
}
