import React from "react";
import type { QuickStatsTickerProps } from "./QuickStatsTicker.types";

const formatGold = (amount: number): string =>
  amount > 0 ? `+${amount}g` : `${amount}g`;

const formatStabilityDelta = (delta: number): string =>
  `(${delta > 0 ? `+${delta}` : delta}%)`;

const getGoldColorClass = (amount: number): string => {
  if (amount > 0) return "text-[#5E8A5A]";
  if (amount < 0) return "text-[#A8483E]";
  return "text-[#3A3128]";
};

const getStabilityColorClass = (delta: number): string => {
  if (delta > 0) return "text-[#5E8A5A]";
  if (delta < 0) return "text-[#A8483E]";
  return "text-[#7A6F62]";
};

interface NetGoldCellProps {
  netGold: number;
}

const NetGoldCell: React.FC<NetGoldCellProps> = ({ netGold }) => (
  <div className="flex min-w-0 flex-col">
    <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
      Net Gold
    </span>
    <span
      className={`text-sm font-semibold font-mono ${getGoldColorClass(netGold)}`}
    >
      {formatGold(netGold)}
    </span>
  </div>
);

interface CasualtiesCellProps {
  totalCasualties: number;
}

const CasualtiesCell: React.FC<CasualtiesCellProps> = ({ totalCasualties }) => (
  <div className="flex min-w-0 flex-col">
    <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
      Casualties
    </span>
    <span className="text-sm font-semibold font-mono text-[#A8483E]">
      {totalCasualties.toLocaleString()}
    </span>
  </div>
);

interface StabilityCellProps {
  stability: number;
  delta: number;
  isEstimated?: boolean;
}

const StabilityCell: React.FC<StabilityCellProps> = ({
  stability,
  delta,
  isEstimated,
}) => (
  <div className="flex min-w-0 flex-col">
    <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
      Stability
    </span>
    <div className="flex flex-wrap items-baseline gap-x-1">
      <span className="text-sm font-semibold font-mono text-[#3A3128]">
        {stability}%
      </span>
      <span
        className={`text-xs font-mono font-medium ${getStabilityColorClass(delta)}`}
      >
        {formatStabilityDelta(delta)}
      </span>
      {isEstimated ? (
        <span className="text-[10px] italic text-[#7A6F62]">[Estimated]</span>
      ) : null}
    </div>
  </div>
);

interface ManpowerCellProps {
  manpower: number;
  isEstimated?: boolean;
}

const ManpowerCell: React.FC<ManpowerCellProps> = ({
  manpower,
  isEstimated,
}) => (
  <div className="flex min-w-0 flex-col">
    <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
      Manpower
    </span>
    <div className="flex flex-wrap items-baseline gap-x-1">
      <span className="text-sm font-semibold font-mono text-[#3A3128]">
        {manpower.toLocaleString()}
      </span>
      {isEstimated ? (
        <span className="text-[10px] italic text-[#7A6F62]">[Estimated]</span>
      ) : null}
    </div>
  </div>
);

export const QuickStatsTicker: React.FC<QuickStatsTickerProps> = ({
  stats,
  estimatedSections,
}) => {
  const isEstimatedStability = Boolean(
    estimatedSections?.includes("stability_delta"),
  );
  const isEstimatedManpower = Boolean(
    estimatedSections?.includes("manpower_delta"),
  );

  return (
    <div className="grid grid-cols-4 gap-2 p-2 bg-[#F3EAD3]/60 rounded-lg border border-[#3A3128]/15">
      <NetGoldCell netGold={stats.netGold} />
      <CasualtiesCell totalCasualties={stats.totalCasualties} />
      <StabilityCell
        stability={stats.stability}
        delta={stats.stabilityDelta}
        isEstimated={isEstimatedStability}
      />
      <ManpowerCell
        manpower={stats.manpower}
        isEstimated={isEstimatedManpower}
      />
    </div>
  );
};
