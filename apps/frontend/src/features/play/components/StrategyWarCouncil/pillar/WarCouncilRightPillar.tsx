import type { TacticType, TerrainType } from "../StrategyWarCouncil.types";
import { CommitPillar } from "./CommitPillar";
import { TacticalDoctrinesList } from "./TacticalDoctrinesList";

export interface WarCouncilRightPillarProps {
  selectedTactic: TacticType;
  onSelectTactic: (tactic: TacticType) => void;
  cavalryCount: number;
  terrain: TerrainType;
  frontlineCount: number;
  reserveCount?: number;
  oddsBadgeText: string;
  isCommitting: boolean;
  isCommitDisabled?: boolean;
  commitErrorMessage?: string | null;
  commitNoticeMessage?: string | null;
  onCommit: () => void;
}

export function WarCouncilRightPillar({
  selectedTactic,
  onSelectTactic,
  cavalryCount,
  terrain,
  frontlineCount,
  reserveCount,
  oddsBadgeText,
  isCommitting,
  isCommitDisabled,
  commitErrorMessage,
  commitNoticeMessage,
  onCommit,
}: WarCouncilRightPillarProps) {
  return (
    <aside className="w-full lg:w-[24%] lg:h-full flex flex-col bg-[#F7F0DC]/95 lg:backdrop-blur-md border-t lg:border-t-0 lg:border-l border-[#3A3128]/15 z-20 p-3.5 gap-3 shadow-md justify-between">
      <div className="flex flex-col gap-2.5 lg:overflow-y-auto">
        <div className="border-b pb-1 flex items-center justify-between border-[#3A3128]/10">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[#2e4856] text-[18px]">military_tech</span>
            <h2 className="font-serif text-[17px] text-[#221a12]">Tactical Doctrines</h2>
          </div>
          <span className="text-[10px] uppercase tracking-wider text-[#42474b]">War Council</span>
        </div>
        <TacticalDoctrinesList
          selectedTactic={selectedTactic}
          onSelectTactic={onSelectTactic}
          cavalryCount={cavalryCount}
          terrain={terrain}
        />
      </div>

      <CommitPillar
        frontlineCount={frontlineCount}
        reserveCount={reserveCount}
        oddsBadgeText={oddsBadgeText}
        isCommitting={isCommitting}
        isDisabled={isCommitDisabled}
        errorMessage={commitErrorMessage}
        noticeMessage={commitNoticeMessage}
        onCommit={onCommit}
      />
    </aside>
  );
}
