import React, { useEffect, useRef } from "react";
import type { NegotiationReadingChamberProps } from "./NegotiationReadingChamber.types";

export const NegotiationReadingChamber: React.FC<NegotiationReadingChamberProps> = ({
  situation,
  transcript,
  leaderName,
  pendingPlayerText,
  streamingReply,
  isStreaming = false,
  warningMessage,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, pendingPlayerText, streamingReply]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-16 py-10 space-y-9 relative z-10 max-w-4xl mx-auto w-full"
      aria-label="Negotiation Chamber Transcript"
      aria-live="polite"
    >
      {situation ? (
        <article className="bg-surface-container/50 p-6 rounded-xl shadow-sm leading-relaxed text-on-surface-variant font-serif text-lg border border-outline-variant/30">
          <p className="first-letter:text-4xl first-letter:font-serif first-letter:text-on-surface first-letter:float-left first-letter:mr-3 first-letter:leading-none">
            {situation}
          </p>
        </article>
      ) : null}

      {transcript.map((ex) => (
        <React.Fragment key={ex.sequence}>
          {ex.player_text.trim() ? (
            <div className="space-y-1.5 pr-2">
              <div className="flex items-center gap-2 justify-end">
                <span className="font-sans text-xs text-outline">Exchanged</span>
                <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
                <span className="font-sans text-xs tracking-wider uppercase font-semibold text-secondary">
                  You spoke
                </span>
              </div>
              <div className="bg-surface-container-low/90 p-5 rounded-l-xl rounded-br-xl shadow-sm relative overflow-hidden pl-7 border border-outline-variant/30">
                <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-secondary" />
                <p className="font-sans text-base text-on-surface leading-relaxed">
                  &ldquo;{ex.player_text}&rdquo;
                </p>
              </div>
            </div>
          ) : null}

          <div className="space-y-1.5 pl-2">
            <div className="flex items-center gap-2">
              <span className="font-sans text-xs tracking-wider uppercase font-semibold text-primary">
                {leaderName}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-outline-variant" />
              <span className="font-sans text-xs text-outline">Addressed the chamber</span>
            </div>
            <div className="bg-parchment-panel/90 p-5 rounded-r-xl rounded-bl-xl shadow-sm text-on-surface border border-outline-variant/30">
              <blockquote className="font-serif text-xl italic text-on-surface tracking-wide leading-relaxed font-normal">
                &ldquo;{ex.leader_text}&rdquo;
              </blockquote>
            </div>
          </div>
        </React.Fragment>
      ))}

      {pendingPlayerText ? (
        <div className="space-y-1.5 pr-2">
          <div className="flex items-center gap-2 justify-end">
            <span className="font-sans text-xs text-outline">Just now</span>
            <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
            <span className="font-sans text-xs tracking-wider uppercase font-semibold text-secondary">
              You spoke
            </span>
          </div>
          <div className="bg-surface-container-low/90 p-5 rounded-l-xl rounded-br-xl shadow-sm relative overflow-hidden pl-7 border border-outline-variant/30">
            <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-secondary" />
            <p className="font-sans text-base text-on-surface leading-relaxed">
              &ldquo;{pendingPlayerText}&rdquo;
            </p>
          </div>
        </div>
      ) : null}

      {isStreaming || streamingReply ? (
        <div className="space-y-1.5 pl-2 animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="font-sans text-xs tracking-wider uppercase font-semibold text-primary">
              {leaderName}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-outline-variant" />
            <span className="font-sans text-xs text-outline italic">Deliberating...</span>
          </div>
          <div className="bg-parchment-panel/90 p-5 rounded-r-xl rounded-bl-xl shadow-sm text-on-surface border border-outline-variant/30">
            <blockquote className="font-serif text-xl italic text-on-surface tracking-wide leading-relaxed font-normal">
              &ldquo;{streamingReply || "…"}&rdquo;
            </blockquote>
          </div>
        </div>
      ) : null}

      {warningMessage ? (
        <div className="flex justify-center my-4">
          <div className="inline-flex items-center gap-2 bg-surface-container-high/90 text-on-surface font-sans text-xs px-4 py-1.5 rounded-full shadow-inner border border-tertiary/40">
            <span className="material-symbols-outlined text-[16px] text-tertiary">
              warning
            </span>
            <span>{warningMessage}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
