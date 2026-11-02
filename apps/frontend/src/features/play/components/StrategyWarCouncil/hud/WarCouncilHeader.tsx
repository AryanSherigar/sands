import { AtmosphericConditionChip } from "./AtmosphericConditionChip";

export interface WarCouncilHeaderProps {
  regionName: string;
  battleTitle: string;
  turnText: string;
  terrainName: string;
  weatherName: string;
  isMuted: boolean;
  onToggleAudio: () => void;
  onOpenCodex: () => void;
  onOpenRetreat: () => void;
  onReturnToMap: () => void;
  mandatesText?: string;
  frontageText?: string;
  isRetreatDisabled?: boolean;
}

export function WarCouncilHeader({
  regionName,
  battleTitle,
  turnText,
  terrainName,
  weatherName,
  isMuted,
  onToggleAudio,
  onOpenCodex,
  onOpenRetreat,
  onReturnToMap,
  mandatesText,
  frontageText,
  isRetreatDisabled = false,
}: WarCouncilHeaderProps) {
  return (
    <header className="relative z-30 flex flex-wrap items-center justify-between gap-2 px-3 py-2 sm:px-4 bg-[#F7F0DC]/95 backdrop-blur-md border-b border-[#3A3128]/10 shrink-0">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={onReturnToMap}
          className="group flex items-center gap-1 px-2.5 py-1 rounded bg-[#fff8f4]/60 hover:bg-[#fff8f4] text-[#2e4856] transition cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px] group-hover:-translate-x-0.5 transition-transform">arrow_back</span>
          <span className="text-[12px] tracking-wide uppercase font-semibold">Map of {regionName}</span>
        </button>
        <span className="text-[#c2c7cb] select-none">|</span>
        <div className="flex items-baseline gap-2">
          <h1 className="font-serif text-[20px] text-[#221a12] tracking-wide font-semibold">{battleTitle}</h1>
          <span className="text-[12px] text-[#42474b] italic">{turnText}</span>
        </div>
        {mandatesText ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold font-sans uppercase tracking-wider bg-[#FAF0D4] text-[#785A00] border border-[#D2A94A]/60 shadow-sm">
            {mandatesText}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <AtmosphericConditionChip weather={weatherName} terrain={terrainName} />
        {frontageText ? (
          <span className="rounded-md border border-[#A8483E]/20 bg-[#A8483E]/10 px-2.5 py-1 font-sans text-[12px] font-bold text-[#A8483E]">
            {frontageText}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onOpenCodex}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded hover:bg-[#f5e5d8] transition text-[#42474b] cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">menu_book</span>
          <span className="hidden text-[11px] tracking-wider uppercase font-semibold lg:inline">Codex Tactics</span>
        </button>
        <button
          type="button"
          onClick={onToggleAudio}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded hover:bg-[#f5e5d8] transition text-[#42474b] cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">{isMuted ? "volume_off" : "volume_up"}</span>
          <span className="hidden text-[11px] tracking-wider font-medium lg:inline">Horns & Wind</span>
        </button>
        <button
          type="button"
          onClick={onOpenRetreat}
          disabled={isRetreatDisabled}
          className="px-3 py-1 rounded bg-[#fff8f4] text-[#7c2820] hover:bg-[#fff1e6] text-[11px] uppercase tracking-wider transition shadow-sm border border-[#3A3128]/10 cursor-pointer font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Retreat to Camp
        </button>
      </div>
    </header>
  );
}
