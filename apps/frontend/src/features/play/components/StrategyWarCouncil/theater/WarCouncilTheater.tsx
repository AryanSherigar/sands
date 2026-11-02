import type {
  FormationType,
  MissionTarget,
  OpponentView,
  RankTier,
  ReservePolicyType,
  WardConfig,
  WardIdentifier,
} from "../StrategyWarCouncil.types";
import { EnemyCrestIntel } from "./EnemyCrestIntel";
import { PlayerWardRanks } from "./PlayerWardRanks";
import { ReservesDeck } from "./ReservesDeck";

export interface WarCouncilTheaterProps {
  opponent: OpponentView;
  formation?: FormationType;
  anchorSlot?: WardIdentifier;
  onSelectSlot?: (slot: WardIdentifier) => void;
  wards: Record<string, WardConfig>;
  onUpdateCohortCount: (ward: WardIdentifier, rankOrder: RankTier, delta: number) => void;
  onReorderRank: (ward: WardIdentifier, fromRank: RankTier, toRank: RankTier) => void;
  onSelectAnchor?: (ward: WardIdentifier) => void;
  troops?: Record<string, number>;
  morale?: number;
  reservePolicy: ReservePolicyType;
  onChangeReservePolicy: (policy: ReservePolicyType) => void;
  isSendingCommand?: boolean;
  canCommitReserves: boolean;
  onCommitReserves: () => void;
  canScout: boolean;
  onOrderScout: (target: MissionTarget) => void;
  clashDividerText?: string;
  frontageSubtext?: string;
}

function describeScouting(opponent: OpponentView): string {
  const latestTurn = Math.max(0, ...opponent.reports.map((report) => report.observed_turn));
  if (opponent.reports.length === 0) return "No scouting reports yet";
  return `Latest scouting report from turn ${latestTurn}`;
}

export function WarCouncilTheater({
  opponent,
  onSelectSlot,
  wards,
  onUpdateCohortCount,
  onReorderRank,
  onSelectAnchor,
  reservePolicy,
  onChangeReservePolicy,
  isSendingCommand = false,
  canCommitReserves,
  onCommitReserves,
  canScout,
  onOrderScout,
  clashDividerText = "Field of Battle",
  frontageSubtext,
}: WarCouncilTheaterProps) {
  const handleSelectAnchor = onSelectAnchor ?? onSelectSlot;

  return (
    <section className="w-full lg:w-[52%] lg:h-full relative lg:overflow-y-auto overflow-x-hidden flex flex-col justify-between bg-[#F3EAD3] p-3 gap-3">
      {/* Painterly contours & mist background */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30" fill="none" viewBox="0 0 1000 900">
        <path d="M 0 240 C 250 220, 500 250, 750 230 C 850 220, 950 240, 1000 220" stroke="#785a00" strokeDasharray="4 6" strokeWidth="1.5" />
        <path d="M 0 460 C 260 450, 480 500, 680 470 C 860 440, 950 480, 1000 460" stroke="#46606e" strokeLinecap="round" strokeWidth="3.5" />
        <circle cx="500" cy="480" r="36" stroke="#785a00" strokeDasharray="3 4" strokeWidth="1.5" />
      </svg>

      {/* Top: Enemy Crest Intel */}
      <div className="relative z-10 w-full">
        <EnemyCrestIntel scoutedTurnText={describeScouting(opponent)} opponent={opponent} canScout={canScout} isSending={isSendingCommand} onOrderScout={onOrderScout} />
      </div>

      {/* Clash Divider: River/Pass Bottleneck */}
      <div className="relative z-10 w-full flex flex-col gap-1.5 my-1">
        <div className="h-9 rounded-lg bg-[repeating-linear-gradient(45deg,#C7D8DE,#C7D8DE_15px,#D5E4E8_15px,#D5E4E8_30px)] border border-[#B0C4DE] flex items-center justify-center shadow-sm">
          <span className="bg-[#F7F0DC]/95 px-3 py-0.5 rounded-full text-[11px] font-bold font-sans text-[#46606E] border border-[#46606E] shadow-sm uppercase tracking-wider">
            {clashDividerText}
          </span>
        </div>
        <div className="flex items-center justify-between px-1">
          <span className="text-[12px] font-sans font-bold text-[#46606E] uppercase tracking-wider">
            Our Battle Array (Planning Sketch — Not Sent to the Field)
          </span>
          {frontageSubtext ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold font-sans bg-[#E8F0E8] text-[#5E8A5A] border border-[#5E8A5A]/50">
              {frontageSubtext}
            </span>
          ) : null}
        </div>
      </div>

      {/* Bottom: Player Ward Ranks and Reserves Deck */}
      <div className="relative z-10 flex flex-col items-center gap-3">
        <PlayerWardRanks
          wards={wards}
          onUpdateCohortCount={onUpdateCohortCount}
          onReorderRank={onReorderRank}
          onSelectAnchor={handleSelectAnchor}
        />
        <ReservesDeck
          reservePolicy={reservePolicy}
          onChangePolicy={onChangeReservePolicy}
          canCommitReserves={canCommitReserves}
          isSending={isSendingCommand}
          onCommitReserves={onCommitReserves}
        />
      </div>
    </section>
  );
}
