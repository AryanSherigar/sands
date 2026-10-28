import React from "react";
import { IconAlertTriangle, IconCoins, IconUsers } from "@tabler/icons-react";
import type {
  StrategyFactionDossierProps,
  FactionCrisisInfo,
} from "./StrategyRulerSetup.types";

const CRISIS_CATALOG: Record<string, FactionCrisisInfo> = {
  valenreach: {
    title: "Autumn Equinox Crisis",
    tag: "Critical Incident",
    description:
      "An early frost has spoiled the grain yields across Highgard's outer basin. Hostile raids along the northern frontier demand immediate garrisoning or grain rationing.",
  },
  oakhaven: {
    title: "Border Timber Skirmish",
    tag: "Border Incident",
    description:
      "Highland raiding companies have seized three western timber mills. The March councils demand an armed retaliation before winter rains close the mountain passes.",
  },
  ironmark: {
    title: "Vanguard Pay Deficit",
    tag: "Military Discontent",
    description:
      "Ironmark heavy cavalry battalions are owed seasonal bounties. Quartermasters warn that delayed silver will erode garrison discipline on the outer ramparts.",
  },
  riverlands: {
    title: "Toll Canal Blockade",
    tag: "Trade Dispute",
    description:
      "Rival river barons have sunk barges across the Lower Estuary channels. Merchant guilds urge immediate clearing operations to safeguard annual grain tariff receipts.",
  },
};

export const StrategyFactionDossier: React.FC<StrategyFactionDossierProps> = ({
  faction,
}) => {
  if (!faction) return null;

  const crisis =
    faction.crisis ??
    CRISIS_CATALOG[faction.id] ?? {
      title: "Borderland Frontier Crisis",
      tag: "Critical Incident",
      description:
        "Tensions flare across the contested marches. Local lords demand sovereign intervention and military provisions before roads freeze.",
    };

  const provinceCount = faction.provinces_count ?? 1;
  const provinceLabel = `${provinceCount} Fertile ${provinceCount === 1 ? "Province" : "Provinces"}`;

  return (
    <div className="bg-[#F7F0DC]/90 backdrop-blur-md p-4 rounded-xl shadow-md flex flex-col gap-3 border border-[#3A3128]/10">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-[11px] font-semibold tracking-wider uppercase text-[#2e4856] font-['Manrope',sans-serif]">
            Realm Dossier
          </span>
          <h3 className="text-[20px] font-semibold text-[#221a12] font-['EB_Garamond',serif]">
            {faction.name.startsWith("The ") ? faction.name : `The ${faction.name}`}
          </h3>
        </div>
        <div className="text-right">
          <span className="text-[11px] text-[#72787c] block uppercase font-['Manrope',sans-serif]">
            Territory Scope
          </span>
          <span className="text-[13px] font-bold text-[#221a12] font-['Manrope',sans-serif] tabular-nums">
            {provinceLabel}
          </span>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
        <div className="p-2 rounded bg-[#fff1e6] shadow-xs flex flex-col border border-[#3A3128]/5">
          <span className="text-[11px] text-[#42474b] font-['Manrope',sans-serif]">Capital Seat</span>
          <span className="text-[15px] font-semibold text-[#221a12] font-['EB_Garamond',serif] truncate">
            {faction.capital_seat || "Castle Seat"}
          </span>
        </div>
        <div className="p-2 rounded bg-[#fff1e6] shadow-xs flex flex-col border border-[#3A3128]/5">
          <span className="text-[11px] text-[#42474b] font-['Manrope',sans-serif]">Government</span>
          <span className="text-[15px] font-semibold text-[#221a12] font-['EB_Garamond',serif] truncate">
            {faction.government || "Feudal Monarchy"}
          </span>
        </div>
        <div className="p-2 rounded bg-[#fff1e6] shadow-xs flex flex-col border border-[#3A3128]/5">
          <span className="text-[11px] text-[#42474b] font-['Manrope',sans-serif]">Treasury</span>
          <span className="text-[14px] font-bold text-[#785a00] font-['Manrope',sans-serif] tabular-nums flex items-center gap-1">
            <IconCoins size={15} className="shrink-0" />
            <span>{faction.treasury.toLocaleString()} Gold</span>
          </span>
        </div>
        <div className="p-2 rounded bg-[#fff1e6] shadow-xs flex flex-col border border-[#3A3128]/5">
          <span className="text-[11px] text-[#42474b] font-['Manrope',sans-serif]">Manpower</span>
          <span className="text-[14px] font-bold text-[#2e4856] font-['Manrope',sans-serif] tabular-nums flex items-center gap-1">
            <IconUsers size={15} className="shrink-0" />
            <span>{faction.manpower.toLocaleString()}</span>
          </span>
        </div>
      </div>

      {/* Starting Crisis Banner */}
      <div className="p-3 rounded-lg bg-[#f5e5d8]/80 flex items-start gap-3 mt-1 shadow-xs border border-[#7c2820]/20">
        <IconAlertTriangle size={20} className="text-[#7c2820] mt-0.5 shrink-0" />
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-bold text-[#7c2820] font-['Manrope',sans-serif]">
              {crisis.title}
            </span>
            <span className="text-[10px] uppercase font-semibold bg-[#7c2820]/10 text-[#7c2820] px-1.5 py-0.5 rounded">
              {crisis.tag || "Critical Incident"}
            </span>
          </div>
          <p className="text-[12px] text-[#42474b] font-['Manrope',sans-serif] mt-0.5 leading-relaxed">
            {crisis.description}
          </p>
        </div>
      </div>
    </div>
  );
};
