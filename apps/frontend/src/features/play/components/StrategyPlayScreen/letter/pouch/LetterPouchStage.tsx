import React from "react";
import type { LetterPouchStageProps } from "./LetterPouchStage.types";
import { LetterProvenanceFlap } from "./LetterProvenanceFlap";
import { LetterManuscriptSheet } from "./LetterManuscriptSheet";
import { LetterReplyDocketsFlap } from "./LetterReplyDocketsFlap";

function CourierDispatchBadge() {
  return (
    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-5 py-0.5 rounded-full bg-[#523d24] text-[#f7edd2] text-[10px] font-label-md uppercase tracking-[0.2em] shadow-md flex items-center gap-2 z-30">
      <span className="material-symbols-outlined text-[13px] text-secondary-container">local_shipping</span>
      <span>Opened Royal Courier Dispatch</span>
    </div>
  );
}

export const LetterPouchStage: React.FC<LetterPouchStageProps> = ({ pkg, onSelectDocket }) => (
  <div className="relative w-full mt-2 flex flex-col items-center">
    <div className="relative w-full rounded-2xl bg-[#e3d3b0] p-3 sm:p-5 md:p-7 border border-[#c9b78e]/70 shadow-2xl overflow-visible">
      <CourierDispatchBadge />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-6 items-stretch relative">
        <LetterProvenanceFlap provenance={pkg.provenance} dispatchId={pkg.dispatchId} />
        <LetterManuscriptSheet incoming={pkg.incoming} portraitUrl={pkg.provenance.portraitUrl} />
        <LetterReplyDocketsFlap
          senderName={pkg.provenance.senderName}
          isDeclinable={pkg.isDeclinable !== false}
          onSelect={onSelectDocket}
        />
      </div>
    </div>
  </div>
);
