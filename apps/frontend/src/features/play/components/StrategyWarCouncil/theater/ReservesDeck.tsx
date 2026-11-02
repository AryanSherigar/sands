import type { ReservePolicyType } from "../StrategyWarCouncil.types";

export interface ReservesDeckProps {
  reservePolicy: ReservePolicyType;
  onChangePolicy: (policy: ReservePolicyType) => void;
  canCommitReserves: boolean;
  isSending?: boolean;
  onCommitReserves: () => void;
}

const POLICY_OPTIONS: Array<{ policy: ReservePolicyType; label: string }> = [
  { policy: "conserve", label: "Conserve reserves" },
  { policy: "reinforce_on_pressure", label: "Reinforce under pressure" },
];

export function ReservesDeck({
  reservePolicy,
  onChangePolicy,
  canCommitReserves,
  isSending = false,
  onCommitReserves,
}: ReservesDeckProps) {
  return (
    <div className="w-full max-w-[660px] mt-2.5 p-2 px-3 rounded-xl bg-[#F7F0DC]/90 backdrop-blur-md shadow-sm border border-[#3A3128]/10 flex items-center justify-between gap-3">
      <div className="flex items-center gap-1.5 shrink-0">
        <span className="material-symbols-outlined text-[#2e4856] text-[18px]">groups</span>
        <span className="text-[11px] uppercase tracking-wider text-[#221a12] font-bold">Reserves Policy:</span>
      </div>
      <div role="radiogroup" aria-label="Reserve policy" className="flex items-center gap-1.5">
        {POLICY_OPTIONS.map(({ policy, label }) => (
          <button
            key={policy}
            type="button"
            role="radio"
            aria-checked={reservePolicy === policy}
            onClick={() => onChangePolicy(policy)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold cursor-pointer border ${
              reservePolicy === policy
                ? "bg-[#2e4856] text-white border-[#2e4856]"
                : "bg-[#fff8f4] text-[#221a12] border-[#3A3128]/20 hover:bg-[#fbebde]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <button
        type="button"
        disabled={!canCommitReserves}
        aria-busy={isSending}
        onClick={onCommitReserves}
        className="px-3 py-1 rounded-lg bg-[#fed16e] text-[#775900] text-[11px] font-bold border border-[#785a00]/40 cursor-pointer hover:bg-[#ecc15f] active:translate-y-px transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSending ? "Committing…" : "Commit reserves now"}
      </button>
    </div>
  );
}
