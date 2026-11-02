import React from "react";
import type { LetterProvenance } from "../../../../types/letterScene.types";
import type { LetterProvenanceFlapProps } from "./LetterPouchStage.types";
import { TemperamentIcon } from "../TemperamentIcon";

function DossierHeader({ dispatchId }: { dispatchId: string }) {
  return (
    <div className="flex items-center justify-between pb-3 border-b border-on-surface/10">
      <span className="text-[10px] font-label-md uppercase tracking-widest text-on-surface-variant/80 font-bold flex items-center gap-1.5">
        <span className="material-symbols-outlined text-[14px] text-secondary">verified</span>
        Courier Outrider Dossier
      </span>
      <span className="text-[10px] font-mono text-on-surface-variant/70">{dispatchId}</span>
    </div>
  );
}

function SenderIdentityCard({ provenance }: { provenance: LetterProvenance }) {
  return (
    <div className="flex items-center gap-3 bg-parchment-panel/85 p-3 rounded-lg shadow-xs border border-[#cfbd94]/60">
      <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-secondary/50 flex-shrink-0 shadow-sm">
        {provenance.portraitUrl ? (
          <img
            src={provenance.portraitUrl}
            alt={provenance.senderName}
            className="w-full h-full object-cover object-top"
          />
        ) : null}
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[9px] font-label-md tracking-wider uppercase text-on-surface-variant font-bold">
          Sender
        </span>
        <h3 className="font-headline-sm text-title-md font-semibold text-on-surface leading-tight truncate">
          {provenance.senderName}
        </h3>
        <span className="font-display italic text-body-sm text-on-surface-variant/90">
          {provenance.senderKeep}
        </span>
      </div>
    </div>
  );
}

function ProvenanceDetails({ provenance }: { provenance: LetterProvenance }) {
  return (
    <>
      <div className="px-3 py-2 rounded-lg bg-surface-container-low/90 border border-outline-variant/40 flex items-center justify-between">
        <span className="font-label-md text-[11px] font-semibold text-on-surface">{provenance.senderTitle}</span>
        <span className="material-symbols-outlined text-[16px] text-secondary">crown</span>
      </div>
      <div className="flex flex-col gap-1.5 pt-1">
        <span className="font-label-md text-[10px] tracking-wider uppercase text-on-surface-variant/80">
          Royal Temperament
        </span>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-high/90 text-on-surface shadow-xs">
          <TemperamentIcon name={provenance.temperamentIcon} />
          <span className="font-label-lg text-body-sm font-semibold text-meadow-green">{provenance.temperament}</span>
        </div>
      </div>
      <div className="flex flex-col gap-2 text-body-sm text-on-surface-variant pt-1">
        <div className="flex items-start gap-2">
          <span className="material-symbols-outlined text-[17px] text-primary flex-shrink-0 mt-0.5">near_me</span>
          <span className="leading-snug text-[13px]">{provenance.outriderLog}</span>
        </div>
        <div className="flex items-center gap-2 text-[12px] text-on-surface-variant/85 pl-0.5">
          <span className="material-symbols-outlined text-[15px]">distance</span>
          <span>{provenance.distanceLeagues} leagues along the River Dun</span>
        </div>
      </div>
      <div className="bg-surface-container-low/90 rounded-lg p-3 text-[13px] text-on-surface-variant italic font-display leading-relaxed border-l-2 border-secondary/60">
        “{provenance.historicTieNote}”
      </div>
    </>
  );
}

export const LetterProvenanceFlap: React.FC<LetterProvenanceFlapProps> = ({
  provenance,
  dispatchId,
}) => (
  <aside className="lg:col-span-3 flex flex-col justify-between rounded-xl bg-gradient-to-br from-[#ebe1c7] to-[#dfd1ae] p-5 shadow-inner border border-[#d2c29c]/80 relative overflow-hidden order-2 lg:order-1">
    <div className="flex flex-col gap-4 relative z-10">
      <DossierHeader dispatchId={dispatchId} />
      <SenderIdentityCard provenance={provenance} />
      <ProvenanceDetails provenance={provenance} />
    </div>
  </aside>
);
