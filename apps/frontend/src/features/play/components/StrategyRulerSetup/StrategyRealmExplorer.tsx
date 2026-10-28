import React from "react";
import type { StrategyRealmExplorerProps } from "./StrategyRulerSetup.types";
import { StrategySetupMap } from "./StrategySetupMap";
import { StrategyFactionStrip } from "./StrategyFactionStrip";
import { StrategyFactionDossier } from "./StrategyFactionDossier";

export const StrategyRealmExplorer: React.FC<StrategyRealmExplorerProps> = ({
  factions,
  activeFactionId,
  onSelectFaction,
  mapDoc,
}) => {
  const activeFaction =
    factions.find((f) => f.id === activeFactionId) ?? factions[0];

  return (
    <section className="xl:col-span-6 flex flex-col gap-4">
      {/* Faction Selector Header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <h2 className="text-[24px] font-semibold text-[#221a12] font-['EB_Garamond',serif]">
            Choose Your Realm &amp; Faction
          </h2>
          <span className="text-[11px] font-semibold text-[#2e4856] tracking-wide bg-[#2e4856]/10 px-2 py-0.5 rounded font-['Manrope',sans-serif]">
            {factions.length} Sovereign Powers
          </span>
        </div>
        <p className="text-[14px] text-[#42474b] italic font-['Manrope',sans-serif]">
          Select a realm to sovereign in the Anno 1042 campaign. The land bears memory of treaties long broken.
        </p>
      </div>

      {/* Interactive Watercolor Map Preview Container */}
      <StrategySetupMap
        mapDoc={mapDoc}
        factions={factions}
        activeFactionId={activeFactionId}
        onSelectFaction={onSelectFaction}
      />

      {/* 4-Faction Selection Horizontal Strip */}
      <StrategyFactionStrip
        factions={factions}
        activeFactionId={activeFactionId}
        onSelectFaction={onSelectFaction}
      />

      {/* Selected Faction In-Depth Summary Card */}
      <StrategyFactionDossier faction={activeFaction} />
    </section>
  );
};
