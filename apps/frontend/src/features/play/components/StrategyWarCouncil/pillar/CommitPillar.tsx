export interface CommitPillarProps {
  frontlineCount: number;
  reserveCount?: number;
  oddsBadgeText: string;
  isCommitting: boolean;
  isDisabled?: boolean;
  errorMessage?: string | null;
  noticeMessage?: string | null;
  onCommit: () => void;
}

export function CommitPillar({
  frontlineCount,
  reserveCount,
  oddsBadgeText,
  isCommitting,
  isDisabled = false,
  errorMessage,
  noticeMessage,
  onCommit,
}: CommitPillarProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 flex flex-col gap-2 border-t border-[#3A3128]/15 bg-[#F7F0DC] p-3 shadow-[0_-4px_12px_rgba(58,49,40,0.12)] lg:static lg:z-auto lg:bg-transparent lg:p-0 lg:pt-2 lg:shadow-none shrink-0">
      <div className="p-2 rounded-lg bg-[#fff8f4]/80 border border-[#3A3128]/10 flex flex-col gap-0.5">
        <div className="flex justify-between items-center">
          <span className="text-[10px] text-[#42474b] uppercase font-semibold">Summary of Forces</span>
          <span className="text-[11px] font-semibold text-[#5E8A5A]">{oddsBadgeText}</span>
        </div>
        <p className="text-[13px] text-[#221a12] font-bold">
          {reserveCount === undefined
            ? `${frontlineCount.toLocaleString()} Troops in the field`
            : `${frontlineCount.toLocaleString()} Frontline • ${reserveCount.toLocaleString()} Reserve`}
        </p>
      </div>

      {errorMessage ? (
        <p role="alert" className="text-[12px] text-[#A8483E]">
          {errorMessage}
        </p>
      ) : null}

      {noticeMessage && !errorMessage ? (
        <p role="status" className="strategy-fade text-[12px] text-[#3B6638]">
          {noticeMessage}
        </p>
      ) : null}

      <button
        type="button"
        disabled={isCommitting || isDisabled}
        onClick={onCommit}
        className="w-full py-3 px-4 rounded-xl bg-[#fed16e] text-[#775900] hover:bg-[#ecc15f] transition shadow-md hover:shadow-lg font-serif text-[18px] tracking-wide flex items-center justify-center gap-2 cursor-pointer active:translate-y-0.5 border border-[#785a00]/40 font-semibold disabled:opacity-50"
      >
        <span>{isCommitting ? "Resolving Clash…" : "Commit to Battle"}</span>
        <span className="material-symbols-outlined text-[20px]">swords</span>
      </button>
    </div>
  );
}
