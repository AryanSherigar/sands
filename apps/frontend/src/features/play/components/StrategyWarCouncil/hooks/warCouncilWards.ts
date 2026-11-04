import type {
  RankTier,
  TroopClassification,
  WardConfig,
  WardIdentifier,
  WardRankCohort,
} from "../StrategyWarCouncil.types";

interface RankTemplate {
  troopType: TroopClassification;
  rankOrder: RankTier;
  name: string;
  tacticalRole: string;
}

interface WardTemplate {
  ward: WardIdentifier;
  title: string;
  isAnchor: boolean;
}

const RANK_TEMPLATES: RankTemplate[] = [
  {
    troopType: "infantry",
    rankOrder: "front",
    name: "Infantry Line",
    tacticalRole: "Holds the front and absorbs the enemy assault",
  },
  {
    troopType: "archers_siege",
    rankOrder: "middle",
    name: "Archers and Siege",
    tacticalRole: "Fires over the front rank into the enemy host",
  },
  {
    troopType: "cavalry",
    rankOrder: "rear",
    name: "Cavalry",
    tacticalRole: "Waits behind the line to strike flanks and pursue",
  },
];

const WARD_TEMPLATES: WardTemplate[] = [
  { ward: "left", title: "Left Ward (Vanguard)", isAnchor: false },
  { ward: "center", title: "Center (Main Battle)", isAnchor: true },
  { ward: "right", title: "Right Ward (Rearguard)", isAnchor: false },
];

const FLANK_WARD_COUNT = 2;
const WARD_COUNT = WARD_TEMPLATES.length;

const splitAcrossWards = (total: number): Record<WardIdentifier, number> => {
  const flankShare = Math.floor(total / WARD_COUNT);
  return {
    left: flankShare,
    right: flankShare,
    center: total - flankShare * FLANK_WARD_COUNT,
  };
};

const buildWardCohorts = (
  ward: WardIdentifier,
  activeTroops: Record<string, number>,
): WardRankCohort[] =>
  RANK_TEMPLATES.map((template) => ({
    id: `c-${ward}-${template.rankOrder}`,
    troopType: template.troopType,
    name: template.name,
    count: splitAcrossWards(activeTroops[template.troopType] ?? 0)[ward],
    rankOrder: template.rankOrder,
    tacticalRole: template.tacticalRole,
  })).filter((cohort) => cohort.count > 0);

export const buildWardsFromContingent = (
  activeTroops: Record<string, number>,
): Record<WardIdentifier, WardConfig> => {
  const entries = WARD_TEMPLATES.map((template): [WardIdentifier, WardConfig] => [
    template.ward,
    {
      ward: template.ward,
      title: template.title,
      stance: "hold",
      isAnchor: template.isAnchor,
      ranks: buildWardCohorts(template.ward, activeTroops),
    },
  ]);
  return Object.fromEntries(entries) as Record<WardIdentifier, WardConfig>;
};
