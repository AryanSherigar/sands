import type { JudgmentCourtLinesProps } from "./StrategyJudgmentDialog.types";

export function JudgmentCourtLines({ lines }: JudgmentCourtLinesProps) {
  return (
    <>
      {lines.map((line, index) =>
        line.kind === "narration" ? (
          <p key={index} className="text-[16px] leading-relaxed text-[#221A12]">
            {line.text}
          </p>
        ) : (
          <div key={index} className="space-y-1 border-l-2 border-[#46606E]/60 pl-4">
            <span className="block text-[13px] font-bold uppercase tracking-wider text-[#46606E]">
              {line.speaker}
            </span>
            <p className="font-serif text-[20px] italic leading-snug text-[#221A12]">
              {`“${line.text}”`}
            </p>
          </div>
        ),
      )}
    </>
  );
}
