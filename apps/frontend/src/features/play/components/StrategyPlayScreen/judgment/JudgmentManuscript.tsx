import { JUDGMENT_CONVENING_MESSAGE } from "../../../constants/judgment.constants";
import { parseCourtText } from "../../../lib/judgment-lines";
import { JudgmentCourtLines } from "./JudgmentCourtLines";
import type { JudgmentManuscriptProps } from "./StrategyJudgmentDialog.types";

const SOVEREIGN_LABEL = "The sovereign";

export function JudgmentManuscript({ pkg, liveText, isStreaming }: JudgmentManuscriptProps) {
  return (
    <div
      aria-live="polite"
      className="rounded-lg border border-[#3A3128]/10 bg-[#F7F0DC]/90 p-6 shadow-[0_8px_30px_-6px_rgba(58,49,40,0.14)]"
    >
      <div className="mx-auto max-w-[68ch] space-y-4">
        {pkg.openingText ? (
          <JudgmentCourtLines lines={parseCourtText(pkg.openingText)} />
        ) : (
          <p className="text-center text-[14px] italic text-[#42474b]">
            {JUDGMENT_CONVENING_MESSAGE}
          </p>
        )}
        {pkg.exchanges.map((exchange) => (
          <div key={exchange.sequence} className="space-y-4">
            <div className="space-y-1 border-l-2 border-[#D2A94A] pl-4">
              <span className="block text-[13px] font-bold uppercase tracking-wider text-[#785a00]">
                {SOVEREIGN_LABEL}
              </span>
              <p className="font-serif text-[20px] italic leading-snug text-[#221A12]">
                {`“${exchange.playerText}”`}
              </p>
            </div>
            <JudgmentCourtLines lines={parseCourtText(exchange.courtText)} />
          </div>
        ))}
        {isStreaming && liveText ? <JudgmentCourtLines lines={parseCourtText(liveText)} /> : null}
      </div>
    </div>
  );
}
