import type { RankTier, WardConfig, WardIdentifier } from "../StrategyWarCouncil.types";
import { WardRankCard } from "./WardRankCard";

export interface PlayerWardRanksProps {
  wards: Record<string, WardConfig>;
  onUpdateCohortCount: (ward: WardIdentifier, rankOrder: RankTier, delta: number) => void;
  onReorderRank: (ward: WardIdentifier, fromRank: RankTier, toRank: RankTier) => void;
  onSelectAnchor?: (ward: WardIdentifier) => void;
  step?: number;
}

const WARD_ORDER: WardIdentifier[] = ["left", "center", "right"];

export function PlayerWardRanks({
  wards,
  onUpdateCohortCount,
  onReorderRank,
  onSelectAnchor,
  step = 50,
}: PlayerWardRanksProps) {
  const wardList = WARD_ORDER.map((id) => wards[id]).filter((w): w is WardConfig => Boolean(w));

  return (
    <div className="w-full max-w-[960px] grid grid-cols-1 md:grid-cols-3 gap-3 items-start">
      {wardList.map((ward) => (
        <WardRankCard
          key={ward.ward}
          ward={ward}
          step={step}
          onUpdateCohortCount={onUpdateCohortCount}
          onReorderRank={onReorderRank}
          onSelectAnchor={onSelectAnchor}
        />
      ))}
    </div>
  );
}
