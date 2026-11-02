import React from "react";
import type { NegotiationRatificationOverlayProps } from "./NegotiationRatificationOverlay.types";

export const NegotiationRatificationOverlay: React.FC<NegotiationRatificationOverlayProps> = ({
  outcome,
  counterpartName,
  onClose,
}) => {
  const isAgreed = outcome?.kind === "terms_card" && outcome.result === "agreed";

  return (
    <div
      className="absolute inset-0 z-40 bg-on-surface/50 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Negotiation Outcome"
    >
      <div className="bg-parchment-panel p-8 rounded-2xl shadow-2xl max-w-lg w-full text-center border-2 border-secondary/50 relative overflow-hidden">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-outline hover:text-on-surface p-1 rounded-lg cursor-pointer"
          aria-label="Close"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>

        <div role="status" className="sr-only">
          {isAgreed ? "The pact is sealed." : "The pact was refused."}
        </div>

        <div className="mx-auto w-20 h-20 rounded-full flex items-center justify-center shadow-lg mb-6 border-2 relative">
          {isAgreed ? (
            <div className="w-full h-full rounded-full bg-secondary-container border-secondary flex items-center justify-center text-secondary shadow-inner">
              <span className="material-symbols-outlined text-[36px]">verified</span>
            </div>
          ) : (
            <div className="w-full h-full rounded-full bg-tertiary-fixed border-tertiary flex items-center justify-center text-tertiary shadow-inner">
              <span className="material-symbols-outlined text-[36px]">heart_broken</span>
            </div>
          )}
        </div>

        <h2 className="font-serif text-3xl font-semibold text-on-surface mb-3">
          {isAgreed ? "Treaty Sealed & Ratified" : "Talks Dissolved Without Agreement"}
        </h2>

        <p className="font-serif text-lg italic text-on-surface-variant leading-relaxed mb-8">
          {isAgreed
            ? `The sovereign pact with ${counterpartName} is sealed under royal wax. Covenants take binding effect in the world.`
            : `The talks with ${counterpartName} concluded without an accord. Envoys withdraw to their respective borders.`}
        </p>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-3 px-6 bg-secondary-container hover:bg-secondary-fixed text-on-secondary-container font-sans text-sm font-bold uppercase tracking-wider rounded-xl shadow-lg transition-transform active:translate-y-0.5 cursor-pointer border border-secondary/40"
        >
          Return to Campaign Map
        </button>
      </div>
    </div>
  );
};
