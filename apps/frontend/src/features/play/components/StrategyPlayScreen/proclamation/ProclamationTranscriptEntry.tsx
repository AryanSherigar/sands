import { PROCLAMATION_SPEAKER_STYLES } from "../../../constants/proclamation.constants";
import { SOVEREIGN_SPEAKER } from "../../../lib/proclamation-lines";
import { ProclamationSovereignEntry } from "./ProclamationSovereignEntry";
import type { ProclamationTranscriptEntryProps } from "./ProclamationTranscriptEntry.types";

export function ProclamationTranscriptEntry({ line }: ProclamationTranscriptEntryProps) {
  if (line.speaker === SOVEREIGN_SPEAKER) return <ProclamationSovereignEntry text={line.text} />;
  const style =
    PROCLAMATION_SPEAKER_STYLES[line.speaker] ?? PROCLAMATION_SPEAKER_STYLES.COUNCIL;
  return (
    <div className={`flex items-start gap-4 border-l-4 pl-4 ${style.ruleClassName}`}>
      <div
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-serif text-sm font-bold shadow-sm ${style.avatarClassName}`}
        aria-hidden="true"
      >
        {style.initial}
      </div>
      <div className="min-w-0 flex-1">
        <span
          className={`mb-1 block text-[11px] font-bold uppercase tracking-[0.1em] ${style.nameClassName}`}
        >
          {style.label}
        </span>
        <blockquote className="font-serif text-[20px] italic leading-relaxed text-on-surface">
          {`“${line.text}”`}
        </blockquote>
      </div>
    </div>
  );
}
