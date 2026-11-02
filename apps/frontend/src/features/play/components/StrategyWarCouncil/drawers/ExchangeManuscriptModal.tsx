import { useRef } from "react";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { MAX_BATTLE_WAVES } from "../../../constants/strategy.constants";
import type { ExchangeReport, ReconReport } from "../StrategyWarCouncil.types";

export interface ExchangeManuscriptModalProps {
  report: ExchangeReport | null;
  morale: number | null;
  isFinalWave: boolean;
  isOpen?: boolean;
  onAdvanceWave: () => void;
  onViewAftermath?: () => void;
}

const TROOP_NAMES: Record<string, string> = {
  infantry: "Spearmen",
  cavalry: "Cavalry",
  archers_siege: "Archers",
};

const PREPARATION_TEXT: Record<string, string> = {
  holding: "holding their ground",
  advancing: "advancing",
  flanking: "moving to flank",
  withdrawing: "falling back",
};

const formatOutcome = (outcome: string): string => outcome.replace(/_/g, " ");

const formatTroopName = (troopType: string): string => TROOP_NAMES[troopType] ?? troopType;

function describeObservation(observation: ReconReport): string {
  const strength = `${observation.strength.minimum.toLocaleString()}–${observation.strength.maximum.toLocaleString()}`;
  const hint = observation.preparation_hint
    ? `, ${PREPARATION_TEXT[observation.preparation_hint] ?? observation.preparation_hint}`
    : "";
  return `Scouts count ${strength} of the enemy${hint} (${observation.confidence} confidence).`;
}

interface ManuscriptHeaderProps {
  waveIndex: number;
  morale: number | null;
  enemyStrength: ExchangeReport["opponent_strength"];
}

function ManuscriptHeader({ waveIndex, morale, enemyStrength }: ManuscriptHeaderProps) {
  const strengthText = `${enemyStrength.minimum.toLocaleString()}–${enemyStrength.maximum.toLocaleString()}`;
  return (
    <div className="flex flex-col gap-2 border-b-2 border-[#D2A94A]/30 pb-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#785a00] text-[26px]">history_edu</span>
          <h2 className="font-serif text-[22px] font-bold text-[#221A12] tracking-wide">
            Wave {waveIndex} Clash Manuscript
          </h2>
        </div>
        <span className="text-[11px] uppercase tracking-wider px-2.5 py-1 rounded bg-[#ebdcb9] text-[#785a00] font-bold border border-[#D2A94A]/40">
          Wave {waveIndex} of {MAX_BATTLE_WAVES}
        </span>
      </div>
      <div className="flex items-center justify-between text-[13px] pt-1">
        <div className="flex items-center gap-2">
          <span className="font-serif text-[#42474b]">Host Cohesion:</span>
          <span className="font-bold text-[#355E3B]">{morale === null ? "Unknown" : `${morale}% Morale`}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-serif text-[#42474b]">Enemy Host (estimated):</span>
          <span className="font-bold text-[#7c2820]">{strengthText}</span>
        </div>
      </div>
    </div>
  );
}

function LossesLedger({ losses }: { losses: Record<string, number> }) {
  const entries = Object.entries(losses);
  return (
    <div className="strategy-rise p-3 rounded-xl bg-[#fffcf5] border border-[#3A3128]/15 shadow-sm flex flex-col gap-1.5">
      <span className="text-[11px] uppercase tracking-wider font-bold text-[#42474b]">
        Our Losses This Wave
      </span>
      {entries.length === 0 ? (
        <p className="text-[13px] text-[#42474b] italic font-serif">No losses reported.</p>
      ) : (
        entries.map(([troopType, fallen]) => (
          <div key={troopType} className="flex items-center justify-between text-[13px]">
            <span className="font-serif font-bold text-[#221A12]">{formatTroopName(troopType)}</span>
            <span className="font-bold text-[#A8483E]">{fallen.toLocaleString()} fallen</span>
          </div>
        ))
      )}
    </div>
  );
}

function OutriderSummary({ observations }: { observations: ReconReport[] }) {
  if (observations.length === 0) return null;
  return (
    <div className="strategy-rise bg-[#ebdcb9]/60 p-3 rounded-xl border border-[#D2A94A]/40 flex items-start gap-2.5">
      <span className="material-symbols-outlined text-[#785a00] text-[20px] mt-0.5">visibility</span>
      <div className="flex flex-col gap-0.5">
        <span className="text-[11px] uppercase tracking-wider font-bold text-[#785a00]">
          Outrider Dispatch
        </span>
        {observations.map((observation) => (
          <p key={observation.id} className="text-[13px] text-[#221A12] italic font-serif">
            {describeObservation(observation)}
          </p>
        ))}
      </div>
    </div>
  );
}

interface ManuscriptFooterProps {
  isFinalWave: boolean;
  onAdvanceWave: () => void;
  onViewAftermath?: () => void;
}

function ManuscriptFooter({
  isFinalWave,
  onAdvanceWave,
  onViewAftermath,
}: ManuscriptFooterProps) {
  const handleClick = isFinalWave ? (onViewAftermath ?? onAdvanceWave) : onAdvanceWave;
  const label = isFinalWave ? "View Aftermath" : "Back to the War Council";
  const colorClass = isFinalWave
    ? "bg-[#7c2820] hover:bg-[#A8483E]"
    : "bg-[#2e4856] hover:bg-[#46606E]";

  return (
    <div className="flex justify-end pt-2 border-t border-[#D2A94A]/30">
      <button
        type="button"
        onClick={handleClick}
        className={`px-5 py-2.5 rounded-xl text-white font-serif font-bold text-[14px] shadow-md cursor-pointer transition-colors ${colorClass}`}
      >
        {label}
      </button>
    </div>
  );
}

export function ExchangeManuscriptModal({
  report,
  morale,
  isFinalWave,
  isOpen = true,
  onAdvanceWave,
  onViewAftermath,
}: ExchangeManuscriptModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const isShowing = isOpen && Boolean(report);
  useFocusTrap(panelRef, isShowing);
  useEscapeKey(isShowing, isFinalWave ? (onViewAftermath ?? onAdvanceWave) : onAdvanceWave);
  if (!isOpen || !report) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Wave ${report.exchange_index} clash manuscript`}
      ref={panelRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#382f26]/60 backdrop-blur-sm"
    >
      <div className="strategy-rise w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#F7F0DC] shadow-2xl p-6 border-2 border-[#D2A94A]/60 flex flex-col gap-4 text-[#221A12]">
        <ManuscriptHeader
          waveIndex={report.exchange_index}
          morale={morale}
          enemyStrength={report.opponent_strength}
        />
        {report.outcome ? (
          <p className="text-[13px] font-serif font-bold capitalize text-[#785a00]">
            {formatOutcome(report.outcome)}
          </p>
        ) : null}
        <LossesLedger losses={report.own_losses} />
        <OutriderSummary observations={report.observations ?? []} />
        <ManuscriptFooter
          isFinalWave={isFinalWave}
          onAdvanceWave={onAdvanceWave}
          onViewAftermath={onViewAftermath}
        />
      </div>
    </div>
  );
}
