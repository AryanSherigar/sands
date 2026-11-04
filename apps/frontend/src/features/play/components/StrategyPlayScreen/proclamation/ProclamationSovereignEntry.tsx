import type { ProclamationSovereignEntryProps } from "./ProclamationTranscriptEntry.types";

const SOVEREIGN_LABEL = "The Sovereign";

export function ProclamationSovereignEntry({ text }: ProclamationSovereignEntryProps) {
  return (
    <div className="flex items-start gap-4 rounded-r-xl border-l-4 border-secondary-container bg-surface-container-low/60 p-4 pl-5 shadow-sm">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary-container text-on-secondary-container">
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
          crown
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <span className="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-secondary">
          {SOVEREIGN_LABEL}
        </span>
        <blockquote className="font-serif text-[24px] italic leading-snug text-on-surface">
          {`“${text}”`}
        </blockquote>
      </div>
    </div>
  );
}
