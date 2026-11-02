import React from "react";
import { ForeignIntrigueActions } from "./ForeignIntrigueActions";
import { findActiveWarId } from "../../../lib/warLookup";
import { resolveOwnerLabel } from "../../../lib/factionLabels";
import type { RegionView } from "../../../types/simulation.types";
import { OccupationNotice } from "./OccupationNotice";
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

interface ForeignCharterActionsProps {
  ownerId: string;
  isAtWar: boolean;
  activeWarId?: string;
  hasTruce: boolean;
  truceLabel?: string;
  onAction?: ProvinceCharterViewProps["onAction"];
}

const ForeignCharterActions: React.FC<ForeignCharterActionsProps> = ({
  ownerId,
  isAtWar,
  activeWarId,
  hasTruce,
  truceLabel,
  onAction,
}) => {
  if (isAtWar) {
    return (
      <div className="p-3 border-t border-[#72787C]/30 flex flex-col gap-2">
        <div className="px-2 py-1 bg-[#A8483E]/10 border border-[#A8483E]/30 rounded text-[#A8483E] text-xs font-bold uppercase tracking-wider text-center">
          Hostile Possession
        </div>
        {activeWarId ? (
          <button
            type="button"
            className="py-1.5 px-2 rounded bg-[#7A2E1D] text-white text-xs font-bold hover:opacity-90 cursor-pointer"
            onClick={() => onAction?.({ type: "sue_peace", warId: activeWarId })}
          >
            Sue for Peace
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="p-3 border-t border-[#72787C]/30 flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={hasTruce}
          title={hasTruce ? truceLabel : undefined}
          className={`py-1.5 px-2 rounded text-xs font-bold cursor-pointer transition-colors ${
            hasTruce
              ? "bg-[#72787C]/20 text-[#72787C] cursor-not-allowed border border-[#72787C]/30"
              : "bg-[#A8483E] text-white hover:opacity-90"
          }`}
          onClick={() => onAction?.({ type: "declare_war", targetFactionId: ownerId })}
        >
          Declare War
        </button>
        <button
          type="button"
          className="py-1.5 px-2 rounded bg-[#46606E] text-white text-xs font-bold hover:opacity-90 cursor-pointer"
          onClick={() => onAction?.({ type: "send_envoy", targetFactionId: ownerId })}
        >
          Send Envoy
        </button>
      </div>
      {hasTruce && truceLabel ? (
        <span className="text-[11px] text-[#A8483E] text-center font-medium">
          {truceLabel}
        </span>
      ) : null}
    </div>
  );
};

function formatUnobservedLabel(lastSeenTurn?: number | null): string {
  return lastSeenTurn ? `Unobserved (T${lastSeenTurn})` : "Unobserved";
}

function findActiveTruce(
  world: ProvinceCharterViewProps["world"],
  myFactionId: string | undefined,
  ownerId: string,
): { hasTruce: boolean; label?: string } {
  if (!world || !myFactionId) return { hasTruce: false };
  const truce = world.truces?.find(
    (t) =>
      (t.faction_a === ownerId && t.faction_b === myFactionId) ||
      (t.faction_b === ownerId && t.faction_a === myFactionId),
  );
  if (truce) {
    return {
      hasTruce: true,
      label: truce.expires_turn ? `Truce active until turn ${truce.expires_turn}` : "Truce active",
    };
  }
  const pact = world.pacts?.find(
    (p) =>
      (p.faction_a === ownerId && p.faction_b === myFactionId) ||
      (p.faction_b === ownerId && p.faction_a === myFactionId),
  );
  if (pact) {
    return {
      hasTruce: true,
      label: `Pact active until turn ${pact.end_turn}`,
    };
  }
  return { hasTruce: false };
}

function resolveProvinceStats(
  regionView?: RegionView,
  myFactionId?: string,
): StatsProps {
  const isFoggedUnowned =
    regionView?.owner_id !== myFactionId && regionView?.visibility === "fogged";
  if (isFoggedUnowned) {
    const unobserved = formatUnobservedLabel(regionView?.last_seen_turn);
    return {
      population: unobserved,
      taxIncome: unobserved,
      manpower: unobserved,
      unrest: unobserved,
    };
  }
  const detail = regionView?.detail;
  return {
    population: detail?.population?.toLocaleString() ?? UNKNOWN_VALUE,
    taxIncome: detail ? `${detail.wealth}g` : UNKNOWN_VALUE,
    manpower: detail?.manpower?.toLocaleString() ?? UNKNOWN_VALUE,
    unrest: detail ? `${detail.unrest}%` : UNKNOWN_VALUE,
  };
}

export const ProvinceCharterView: React.FC<ProvinceCharterViewProps> = ({
  region,
  world,
  onAction,
}) => {
  const regionView = world?.regions.find((item) => item.region_id === region.id);
  const myFactionId = world?.my_faction.id;
  const isOwnRegion = Boolean(world) && regionView?.owner_id === myFactionId;
  const stats = resolveProvinceStats(regionView, myFactionId);

  const ownerId = regionView?.owner_id;
  const isForeignRegion = Boolean(world && ownerId && ownerId !== myFactionId);
  const rival = ownerId ? world?.rivals.find((r) => r.faction_id === ownerId) : undefined;
  const isAtWar = rival?.relation === "war" || rival?.relation === "at_war";
  const activeWarId = isForeignRegion && ownerId ? findActiveWarId(world, myFactionId, ownerId) : undefined;
  const { hasTruce, label: truceLabel } = isForeignRegion && ownerId
    ? findActiveTruce(world, myFactionId, ownerId)
    : { hasTruce: false };

  return (
    <div className="flex flex-col gap-3">
      <ProvinceCharterHeader
        name={region.name}
        terrain={region.terrain}
        ownerLabel={resolveOwnerLabel(world, regionView?.owner_id)}
      />
      <OccupationNotice regionView={regionView} world={world} />
      <ProvinceCharterStats {...stats} />
      {isOwnRegion && (
        <ProvinceCharterActions regionId={region.id} onAction={onAction} />
      )}
      {!isOwnRegion && isForeignRegion && ownerId && (
        <ForeignCharterActions
          ownerId={ownerId}
          isAtWar={isAtWar}
          activeWarId={activeWarId}
          hasTruce={hasTruce}
          truceLabel={truceLabel}
          onAction={onAction}
        />
      )}
      {!isOwnRegion && isForeignRegion && ownerId && (
        <ForeignIntrigueActions regionId={region.id} ownerId={ownerId} onAction={onAction} />
      )}
    </div>
  );
};
