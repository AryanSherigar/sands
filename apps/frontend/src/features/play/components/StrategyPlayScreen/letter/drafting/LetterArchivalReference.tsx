import React from "react";
import type { IncomingLetterContent } from "../../../../types/letterScene.types";
import type { LetterArchivalReferenceProps } from "./LetterDraftingStage.types";
import { TemperamentIcon } from "../TemperamentIcon";

const renderSealVignette = () => (
  <div className="mt-4 pt-3 flex items-center justify-between border-t border-on-surface/10">
    <div className="flex items-center gap-2.5">
      <div className="relative w-10 h-10 flex items-center justify-center">
        <div className="w-4 h-8 bg-tertiary-container rounded-l-full shadow-inner -rotate-6 opacity-90" />
        <div className="w-4 h-8 bg-tertiary rounded-r-full shadow-inner translate-x-1 rotate-6 opacity-90" />
        <span className="material-symbols-outlined absolute text-parchment-base text-[14px]">
          broken_image
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-xs font-semibold text-on-surface">Red wax seal</span>
        <span className="text-[11px] italic font-serif text-on-surface-variant">Broken by courier at dawn</span>
      </div>
    </div>
    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-[#e8dac0] text-on-surface-variant border border-outline-variant/30">
      Archived
    </span>
  </div>
);

const renderChanceryParchment = (incoming: IncomingLetterContent) => (
  <div className="relative bg-[#f5ede0] p-4 sm:p-5 rounded-lg shadow-md border border-[#ded0b1] overflow-hidden text-on-surface-variant">
    <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-[#ded0b1]/50 blur-2xl pointer-events-none" />
    <div className="absolute bottom-4 left-6 w-24 h-24 rounded-full bg-sky-mist/30 blur-xl pointer-events-none" />
    <div className="mb-3 pb-1.5 flex justify-between items-center text-outline border-b border-on-surface/10">
      <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
        Royal Chancery
      </span>
      <span className="material-symbols-outlined text-[16px] opacity-60">bookmark_manager</span>
    </div>
    <div className="flex flex-col gap-2.5 font-serif text-[14px] leading-relaxed text-on-surface-variant/90 italic">
      <p className="font-semibold not-italic text-sm text-on-surface">{incoming.salutation}</p>
      {incoming.paragraphs.map((para, idx) => (
        <p key={idx}>{para}</p>
      ))}
    </div>
    {renderSealVignette()}
  </div>
);

export const LetterArchivalReference: React.FC<LetterArchivalReferenceProps> = ({
  incoming,
  provenance,
}) => (
  <aside className="lg:col-span-4 xl:col-span-4 flex flex-col gap-3">
    <div className="flex items-center justify-between px-1">
      <span className="text-[10px] font-bold tracking-wider uppercase text-on-surface-variant flex items-center gap-1.5">
        <span className="material-symbols-outlined text-[14px]">inventory_2</span>
        Reference: Incoming Dispatch #{incoming.dispatchNumber}
      </span>
      <span className="text-xs text-on-surface-variant italic font-serif">Received at Dawn</span>
    </div>
    <div className="flex items-center gap-3 p-3 rounded-lg bg-parchment-panel/85 backdrop-blur-sm shadow-sm border border-[#cfbd94]/60">
      <div className="relative w-11 h-11 rounded-full overflow-hidden shadow-inner bg-surface-container flex-shrink-0 border border-secondary/40">
        <img src={provenance.portraitUrl} alt={provenance.senderName} className="w-full h-full object-cover" />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-sm font-semibold text-on-surface truncate">{provenance.senderName}</span>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-container text-[11px] font-medium text-on-surface">
            <TemperamentIcon name={provenance.temperamentIcon} />
            <span>{provenance.temperament}</span>
          </span>
        </div>
      </div>
    </div>
    {renderChanceryParchment(incoming)}
  </aside>
);
