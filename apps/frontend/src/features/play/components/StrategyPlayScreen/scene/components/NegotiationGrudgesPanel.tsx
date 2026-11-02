import React from "react";
import type { GrudgeBand } from "../../../../types/scene.types";
import type { NegotiationGrudgesPanelProps } from "./NegotiationGrudgesPanel.types";

const BAND_LABELS: Record<GrudgeBand, string> = {
  faint: "Faint",
  firm: "Firm",
  burning: "Burning",
};

export const NegotiationGrudgesPanel: React.FC<NegotiationGrudgesPanelProps> = ({
  grudges,
  leaderName,
}) => {
  if (grudges.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Held against you"
      className="px-8 py-3 bg-parchment-panel/70 border-b border-outline-variant/30"
    >
      <h2 className="font-sans text-xs uppercase tracking-wider text-on-surface-variant">
        Held against you by {leaderName}
      </h2>
      <ul className="mt-2 flex flex-col gap-1.5">
        {grudges.map((grudge) => (
          <li key={grudge.text} className="flex flex-wrap items-baseline gap-x-2 text-sm text-on-surface">
            <span className="font-serif">{grudge.text}</span>
            <span className="text-xs font-bold text-secondary">{BAND_LABELS[grudge.band]}</span>
            {grudge.is_inherited && (
              <span className="text-xs italic text-on-surface-variant">
                {`inherited from ${grudge.predecessor_name ?? "a predecessor"}`}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
};
