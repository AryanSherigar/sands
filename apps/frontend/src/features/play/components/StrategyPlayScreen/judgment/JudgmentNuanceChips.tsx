import { JUDGMENT_VERDICTS } from "../../../constants/judgment.constants";
import type { JudgmentNuanceChipsProps } from "./StrategyJudgmentDialog.types";

const CHIP_BASE =
  "rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#46606E]";
const CHIP_IDLE = "border-[#3A3128]/10 bg-[#F3EAD3] text-[#221A12] hover:bg-[#f0e0d2]";
const CHIP_ACTIVE = "border-[#2e4856] bg-[#2e4856] text-white";

export function JudgmentNuanceChips({
  verdict,
  selectedNuance,
  onSelectNuance,
}: JudgmentNuanceChipsProps) {
  const definition = JUDGMENT_VERDICTS.find((item) => item.id === verdict);
  if (!definition) return null;
  return (
    <div className="flex flex-col gap-2 rounded border border-[#3A3128]/10 bg-[#fbebde]/60 p-2">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-[#42474b]">
        Decree nuance: {definition.label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {definition.nuances.map((nuance) => (
          <button
            key={nuance.id}
            type="button"
            aria-pressed={selectedNuance === nuance.id}
            onClick={() => onSelectNuance(nuance.id)}
            className={`${CHIP_BASE} ${selectedNuance === nuance.id ? CHIP_ACTIVE : CHIP_IDLE}`}
          >
            {nuance.label}
          </button>
        ))}
      </div>
    </div>
  );
}
