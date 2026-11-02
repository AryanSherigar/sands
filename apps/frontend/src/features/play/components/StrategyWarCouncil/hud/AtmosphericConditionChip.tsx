export interface AtmosphericConditionChipProps {
  weather: string;
  terrain: string;
  tooltipText?: string;
}

export function AtmosphericConditionChip({ weather, terrain, tooltipText }: AtmosphericConditionChipProps) {
  return (
    <div className="relative group cursor-help">
      <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#f5e5d8]/80 shadow-inner text-[12px] hover:bg-[#f5e5d8] transition-colors">
        <span className="material-symbols-outlined text-[#2e4856] text-[18px]">foggy</span>
        <span className="font-semibold text-[#221a12]">{weather}</span>
        <span className="text-[#c2c7cb]">•</span>
        <span className="material-symbols-outlined text-[#5E8A5A] text-[18px]">nature</span>
        <span className="font-semibold text-[#221a12]">{terrain}</span>
      </div>
      {tooltipText ? (
      <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-72 p-3 bg-[#F7F0DC] shadow-md rounded-lg text-[12px] text-[#221a12] hidden group-hover:block z-50 pointer-events-none border border-[#3A3128]/10">
        <p className="font-semibold text-[#2e4856] mb-1">Atmospheric Condition</p>
        <p className="text-[#42474b]">{tooltipText}</p>
      </div>
      ) : null}
    </div>
  );
}
