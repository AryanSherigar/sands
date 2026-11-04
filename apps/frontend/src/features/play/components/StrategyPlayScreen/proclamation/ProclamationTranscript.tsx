import { useEffect, useRef } from "react";
import {
  PROCLAMATION_EMPTY_BODY,
  PROCLAMATION_EMPTY_TITLE,
} from "../../../constants/proclamation.constants";
import { ProclamationTranscriptEntry } from "./ProclamationTranscriptEntry";
import type { ProclamationTranscriptProps } from "./ProclamationTranscript.types";

const STREAMING_LABEL = "The council continues its debate";
const PULSE_DELAYS = ["", "[animation-delay:200ms]", "[animation-delay:400ms]"];

export function ProclamationTranscript({ lines, isStreaming }: ProclamationTranscriptProps) {
  const endRef = useRef<HTMLDivElement>(null);

  const latestTextLength = lines[lines.length - 1]?.text.length ?? 0;

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [lines.length, latestTextLength, isStreaming]);

  const isEmpty = lines.length === 0 && !isStreaming;

  return (
    <section
      aria-label="Transcript of deliberation"
      className="mx-auto w-full max-w-[720px] rounded-xl bg-parchment-panel/90 p-10 shadow-[0_16px_36px_-4px_rgba(58,49,40,0.12),0_4px_12px_-2px_rgba(58,49,40,0.06)] backdrop-blur-md"
    >
      <div className="mb-6 border-b border-on-surface/10 pb-6 text-center">
        <div className="mb-2 inline-flex h-10 w-10 items-center justify-center rounded-full bg-secondary-fixed/50 text-secondary">
          <span className="material-symbols-outlined text-[22px]" aria-hidden="true">
            balance
          </span>
        </div>
        <h2 className="font-serif text-[24px] font-medium tracking-wide text-on-surface">
          Transcript of Deliberation
        </h2>
      </div>
      {isEmpty ? (
        <div className="flex flex-col items-center py-12 text-center">
          <h3 className="font-serif text-[24px] text-on-surface">{PROCLAMATION_EMPTY_TITLE}</h3>
          <p className="mt-2 max-w-md font-serif text-[16px] italic text-on-surface-variant">
            {PROCLAMATION_EMPTY_BODY}
          </p>
        </div>
      ) : (
        <div aria-live="polite" className="flex flex-col gap-6">
          {lines.map((line, index) => (
            <ProclamationTranscriptEntry key={index} line={line} />
          ))}
          {isStreaming ? (
            <div className="flex items-center justify-center gap-2 pt-2 text-on-surface-variant">
              <span className="text-[12px] italic">{STREAMING_LABEL}</span>
              {PULSE_DELAYS.map((delay) => (
                <span
                  key={delay}
                  className={`h-1.5 w-1.5 animate-pulse rounded-full bg-on-surface-variant/60 ${delay}`}
                />
              ))}
            </div>
          ) : null}
        </div>
      )}
      <div ref={endRef} />
    </section>
  );
}
