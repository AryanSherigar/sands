import type {
  RankTier,
  TroopClassification,
  WardConfig,
  WardIdentifier,
  WardRankCohort,
} from "../StrategyWarCouncil.types";
import { IconBow, IconShield, IconStar, IconSwords } from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

export interface WardRankCardProps {
  ward: WardConfig;
  onUpdateCohortCount: (ward: WardIdentifier, rankOrder: RankTier, delta: number) => void;
  onReorderRank: (ward: WardIdentifier, fromRank: RankTier, toRank: RankTier) => void;
  onSelectAnchor?: (ward: WardIdentifier) => void;
  step?: number;
}

const RANK_LABELS: Record<RankTier, string> = {
  front: "1st: Front Rank",
  middle: "2nd: Middle Rank",
  rear: "3rd: Rear Shock",
};

const RANK_BORDER_CLASSES: Record<RankTier, string> = {
  front: "border-l-4 border-l-[#A8483E] bg-[#FFF5F2]",
  middle: "border-l-4 border-l-[#46606E] bg-[#F2F7F9]",
  rear: "border-l-4 border-l-[#785A00] bg-[#FFF9ED]",
};

const RANK_PILL_CLASSES: Record<RankTier, string> = {
  front: "bg-[#FFDAD5] text-[#7C2820]",
  middle: "bg-[#DCE7EA] text-[#2E4856]",
  rear: "bg-[#FED16E] text-[#785A00]",
};

const TROOP_ICONS: Record<TroopClassification, Icon> = {
  infantry: IconShield,
  archers_siege: IconBow,
  cavalry: IconSwords,
};

const NEXT_RANK: Partial<Record<RankTier, RankTier>> = {
  front: "middle",
  middle: "rear",
};

const PREV_RANK: Partial<Record<RankTier, RankTier>> = {
  middle: "front",
  rear: "middle",
};

interface StepperProps {
  onMinus: () => void;
  onPlus: () => void;
  count: number;
}

function RankStepperButtons({ onMinus, onPlus, count }: StepperProps) {
  return (
    <div className="flex items-center gap-1 shrink-0">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onMinus();
        }}
        className="w-[22px] h-[22px] rounded border border-[#C4B59B] bg-[#FDF9F0] text-[#221A12] font-bold text-xs flex items-center justify-center hover:bg-[#46606E] hover:text-white hover:border-[#46606E] transition-colors"
      >
        −
      </button>
      <span className="font-mono font-bold text-xs min-w-[36px] text-center text-[#221A12]">
        {count.toLocaleString()}
      </span>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onPlus();
        }}
        className="w-[22px] h-[22px] rounded border border-[#C4B59B] bg-[#FDF9F0] text-[#221A12] font-bold text-xs flex items-center justify-center hover:bg-[#46606E] hover:text-white hover:border-[#46606E] transition-colors"
      >
        +
      </button>
    </div>
  );
}

interface ReorderProps {
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function RankReorderButtons({ canMoveUp, canMoveDown, onMoveUp, onMoveDown }: ReorderProps) {
  return (
    <div className="flex flex-col gap-0.5 shrink-0 ml-1">
      <button
        type="button"
        disabled={!canMoveUp}
        onClick={(e) => {
          e.stopPropagation();
          onMoveUp();
        }}
        className="w-[18px] h-[12px] flex items-center justify-center text-[10px] text-[#46606E] disabled:opacity-20 hover:text-[#221A12] transition-opacity cursor-pointer disabled:cursor-not-allowed"
      >
        ▲
      </button>
      <button
        type="button"
        disabled={!canMoveDown}
        onClick={(e) => {
          e.stopPropagation();
          onMoveDown();
        }}
        className="w-[18px] h-[12px] flex items-center justify-center text-[10px] text-[#46606E] disabled:opacity-20 hover:text-[#221A12] transition-opacity cursor-pointer disabled:cursor-not-allowed"
      >
        ▼
      </button>
    </div>
  );
}

interface RankSlotRowProps {
  cohort: WardRankCohort;
  step: number;
  onUpdateCount: (delta: number) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function RankSlotRow({ cohort, step, onUpdateCount, onMoveUp, onMoveDown }: RankSlotRowProps) {
  const canMoveUp = PREV_RANK[cohort.rankOrder] !== undefined;
  const canMoveDown = NEXT_RANK[cohort.rankOrder] !== undefined;
  const TroopIcon = TROOP_ICONS[cohort.troopType] ?? IconShield;

  return (
    <div className={`p-2 rounded border border-[#3A3128]/20 flex items-center justify-between gap-2 shadow-sm ${RANK_BORDER_CLASSES[cohort.rankOrder]}`}>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${RANK_PILL_CLASSES[cohort.rankOrder]}`}>
            {RANK_LABELS[cohort.rankOrder]}
          </span>
          <span className="flex items-center gap-1 font-serif font-bold text-xs text-[#221A12] truncate">
            <TroopIcon size={12} aria-hidden="true" />
            {cohort.name}
          </span>
        </div>
        <div className="text-[10px] text-[#72787C] truncate mt-0.5">{cohort.tacticalRole}</div>
      </div>
      <div className="flex items-center">
        <RankStepperButtons count={cohort.count} onMinus={() => onUpdateCount(-step)} onPlus={() => onUpdateCount(step)} />
        <RankReorderButtons canMoveUp={canMoveUp} canMoveDown={canMoveDown} onMoveUp={onMoveUp} onMoveDown={onMoveDown} />
      </div>
    </div>
  );
}

interface WardHeaderProps {
  ward: WardConfig;
  totalMen: number;
}

function WardCardHeader({ ward, totalMen }: WardHeaderProps) {
  return (
    <div className="flex justify-between items-baseline border-b border-[#3A3128]/10 pb-2">
      <div>
        <div className="flex items-center gap-1.5">
          <span className="font-serif font-bold text-[15px] text-[#221A12]">{ward.title}</span>
          {ward.isAnchor && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#FED16E] text-[#785A00] border border-[#D2A94A] text-[10px] font-bold uppercase tracking-wider shadow-sm">
              <IconStar size={10} aria-hidden="true" />
              Tactic Anchor
            </span>
          )}
        </div>
        <div className="text-[11px] text-[#6B5E4F]">
          Total: <strong>{totalMen.toLocaleString()} Men</strong>
        </div>
      </div>
      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#EAE3D2] text-[#6B5E4F]">
        Stance: {ward.stance}
      </span>
    </div>
  );
}

export function WardRankCard({
  ward,
  onUpdateCohortCount,
  onReorderRank,
  onSelectAnchor,
  step = 50,
}: WardRankCardProps) {
  const totalMen = ward.ranks.reduce((sum, r) => sum + r.count, 0);

  const borderClasses = ward.isAnchor
    ? "border-2 border-[#D2A94A] bg-[#FFFDF8] ring-2 ring-[#D2A94A]/25 shadow-md"
    : "border-2 border-[#D5C29D] bg-[#FAF3E3] shadow-sm hover:border-[#46606E]/40";

  return (
    <div
      onClick={() => onSelectAnchor?.(ward.ward)}
      className={`ward-card p-3 rounded-xl flex flex-col gap-2.5 transition cursor-pointer ${borderClasses}`}
    >
      <WardCardHeader ward={ward} totalMen={totalMen} />
      <div className="flex flex-col gap-2">
        {ward.ranks.map((cohort) => (
          <RankSlotRow
            key={cohort.id}
            cohort={cohort}
            step={step}
            onUpdateCount={(delta) => onUpdateCohortCount(ward.ward, cohort.rankOrder, delta)}
            onMoveUp={() => {
              const prev = PREV_RANK[cohort.rankOrder];
              if (prev) onReorderRank(ward.ward, cohort.rankOrder, prev);
            }}
            onMoveDown={() => {
              const next = NEXT_RANK[cohort.rankOrder];
              if (next) onReorderRank(ward.ward, cohort.rankOrder, next);
            }}
          />
        ))}
      </div>
    </div>
  );
}
