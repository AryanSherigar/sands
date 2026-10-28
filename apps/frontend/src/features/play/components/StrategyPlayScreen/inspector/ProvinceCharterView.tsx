import React from "react";
import { resolveOwnerLabel } from "../../../lib/factionLabels";
import type { ProvinceCharterViewProps } from "./ProvinceCharterView.types";

const UNKNOWN_VALUE = "Unknown";

interface StatCardProps {
  label: string;
  value: string;
  textColor?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, textColor }) => (
  <div className="p-2 rounded bg-[#FBEBDE]/60 border border-[#3A3128]/10 flex flex-col">
    <span className="text-[10px] text-[#72787C]">{label}</span>
    <span className={`text-sm font-bold font-mono ${textColor ?? ""}`}>{value}</span>
  </div>
);

interface HeaderProps {
  name: string;
  terrain: string;
  ownerLabel: string;
}

const ProvinceCharterHeader: React.FC<HeaderProps> = ({ name, terrain, ownerLabel }) => (
  <div className="p-3 bg-[#F5E5D8]/60 border-b border-[#72787C]/30 flex flex-col gap-1">
    <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-widest">
      Provincial Charter
    </span>
    <h2 className="text-xl font-bold font-serif text-[#221A12]">{name}</h2>
    <span className="text-xs text-[#42474B] capitalize">{terrain} terrain</span>
    <span className="text-xs text-[#42474B]">Held by {ownerLabel}</span>
  </div>
);

interface StatsProps {
  population: string;
  taxIncome: string;
  manpower: string;
  unrest: string;
}

const ProvinceCharterStats: React.FC<StatsProps> = ({
  population,
  taxIncome,
  manpower,
  unrest,
}) => (
  <div className="grid grid-cols-2 gap-2 p-3">
    <StatCard label="Population" value={population} />
    <StatCard label="Tax Income" value={taxIncome} textColor="text-[#785A00]" />
    <StatCard label="Manpower" value={manpower} textColor="text-[#46606E]" />
    <StatCard label="Unrest" value={unrest} textColor="text-[#A8483E]" />
  </div>
);

interface ActionsProps {
  regionId: string;
  onAction?: ProvinceCharterViewProps["onAction"];
}

const ProvinceCharterActions: React.FC<ActionsProps> = ({ regionId, onAction }) => {
  const handleLevyClick = (): void => {
    onAction?.({ type: "levy", regionId });
  };

  return (
    <div className="p-3 border-t border-[#72787C]/30 grid grid-cols-1 gap-1.5">
      <button
        type="button"
        className="py-1.5 px-2 rounded bg-[#46606E] text-white text-xs font-bold hover:opacity-90"
        onClick={handleLevyClick}
      >
        Levy Troops
      </button>
    </div>
  );
};

export const ProvinceCharterView: React.FC<ProvinceCharterViewProps> = ({
  region,
  world,
  onAction,
}) => {
  const regionView = world?.regions.find((item) => item.region_id === region.id);
  const detail = regionView?.detail;
  const isOwnRegion = Boolean(world) && regionView?.owner_id === world?.my_faction.id;

  return (
    <div className="flex flex-col gap-3">
      <ProvinceCharterHeader
        name={region.name}
        terrain={region.terrain}
        ownerLabel={resolveOwnerLabel(world, regionView?.owner_id)}
      />
      <ProvinceCharterStats
        population={detail?.population?.toLocaleString() ?? UNKNOWN_VALUE}
        taxIncome={detail ? `${detail.wealth}g` : UNKNOWN_VALUE}
        manpower={detail?.manpower?.toLocaleString() ?? UNKNOWN_VALUE}
        unrest={detail ? `${detail.unrest}%` : UNKNOWN_VALUE}
      />
      {isOwnRegion ? (
        <ProvinceCharterActions regionId={region.id} onAction={onAction} />
      ) : null}
    </div>
  );
};
