import React from "react";
import { joinProse, splitProse } from "../../../../lib/letter-prose";
import type { LetterParchmentCanvasProps } from "./LetterDraftingStage.types";

const rawBody = (draft: { paragraphs: string[] }): string => draft.paragraphs.join("\n\n");

const renderFlourishes = () => (
  <>
    <div className="absolute top-3 left-3 text-outline-variant pointer-events-none opacity-40">
      <svg fill="none" height="24" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24" width="24">
        <path d="M2 12C2 6.48 6.48 2 12 2M2 2l10 10M2 2h8M2 2v8" strokeLinecap="round" />
      </svg>
    </div>
    <div className="absolute top-3 right-3 text-outline-variant pointer-events-none opacity-40">
      <svg fill="none" height="24" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24" width="24">
        <path d="M22 12C22 6.48 17.52 2 12 2M22 2L12 12M22 2h-8M22 2v8" strokeLinecap="round" />
      </svg>
    </div>
  </>
);

const EMPTY_DRAFT_HINT = "Ask your scribe for a draft, or take up the quill and write it yourself.";

const renderQuillHeader = () => (
  <div className="flex items-center justify-between mb-2 text-xs font-semibold text-on-surface-variant">
    <span className="flex items-center gap-1.5 text-[#2e4856]">
      <span className="w-2 h-2 rounded-full bg-secondary animate-ping" />
      <span className="font-bold">Active Quill</span>
    </span>
    <span className="text-outline text-[11px] font-sans">[Undo: Ctrl+Z • Auto-blotted]</span>
  </div>
);

const renderDirectQuill = (body: string, onUpdateBody: (text: string) => void) => (
  <div className="relative p-4 rounded-lg bg-[#efe4c8]/70 border border-secondary/30 shadow-inner mb-4">
    {renderQuillHeader()}
    <textarea
      aria-label="Direct quill editing"
      value={body}
      onChange={(e) => onUpdateBody(e.target.value)}
      rows={8}
      className="w-full bg-transparent border-none text-base sm:text-[17px] font-serif text-on-surface leading-relaxed focus:outline-none resize-y p-0"
    />
  </div>
);

const renderReadingBody = (body: string) => {
  const paragraphs = splitProse(body).filter((paragraph) => paragraph.length > 0);
  if (paragraphs.length === 0) {
    return <p className="italic text-on-surface-variant mb-4">{EMPTY_DRAFT_HINT}</p>;
  }
  return paragraphs.map((paragraph, index) => (
    <p
      key={`${index}-${paragraph.slice(0, 12)}`}
      className="text-base sm:text-[17px] text-on-surface/90 leading-relaxed mb-4 whitespace-pre-line"
    >
      {paragraph}
    </p>
  ));
};

const renderCanvasSignoff = (signoffText: string, authorTitle: string) => (
  <div className="mt-4 flex flex-col items-end gap-1.5">
    <p className="italic text-sm text-on-surface-variant font-serif">{signoffText}</p>
    <div className="flex items-center gap-3">
      <div className="flex flex-col text-right">
        <span className="text-xs text-on-surface-variant uppercase tracking-wider">{authorTitle}</span>
      </div>
      <div className="w-11 h-11 rounded-full bg-surface-container flex items-center justify-center text-[#2e4856] shadow-inner border border-[#2e4856]/20">
        <svg fill="none" height="28" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 40 40" width="28">
          <path d="M10 30 C12 18, 22 10, 30 12 C34 14, 28 26, 18 24 C14 23, 12 28, 22 30" strokeLinecap="round" />
          <circle cx="20" cy="20" fill="currentColor" r="1.5" />
        </svg>
      </div>
    </div>
  </div>
);

export const LetterParchmentCanvas: React.FC<LetterParchmentCanvasProps> = ({
  draft,
  isDirectQuill,
  onUpdateBody,
}) => {
  const body = joinProse(draft.paragraphs);
  return (
    <article className="relative bg-parchment-panel rounded-lg shadow-xl p-6 sm:p-8 md:p-10 flex flex-col justify-between overflow-hidden border border-[#ded0b1]">
      {renderFlourishes()}
      <div className="text-center mb-4">
        <span className="text-xs uppercase tracking-widest text-outline font-semibold">Privy Scroll</span>
      </div>
      <div className="flex flex-col text-on-surface font-serif">
        {draft.salutation ? (
          <p className="text-xl sm:text-2xl font-semibold tracking-wide text-on-surface mb-3">{draft.salutation}</p>
        ) : null}
        {isDirectQuill ? renderDirectQuill(rawBody(draft), onUpdateBody) : renderReadingBody(body)}
        {renderCanvasSignoff(draft.signoffText, draft.authorTitle)}
      </div>
    </article>
  );
};
