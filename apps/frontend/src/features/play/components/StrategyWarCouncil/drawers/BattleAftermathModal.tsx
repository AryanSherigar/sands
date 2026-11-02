import { useRef } from "react";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import type { NobleCaptive, StrengthInterval } from "../StrategyWarCouncil.types";

export interface BattleAftermathData {
  outcome: string;
  totalHostLosses: number;
  enemyStrengthRemaining: StrengthInterval | null;
  nobleCaptives?: NobleCaptive[];
  territoryTransferred?: string;
}

export type BattleAftermath = BattleAftermathData;

export interface BattleAftermathModalProps {
  isOpen?: boolean;
  aftermath?: BattleAftermathData | null;
  outcome?: string;
  totalHostLosses?: number;
  enemyStrengthRemaining?: StrengthInterval | null;
  nobleCaptives?: NobleCaptive[];
  onReturnToRealmMap: () => void;
}

function formatOutcomeBanner(outcome: string): string {
  if (outcome === "attacker_victory") {
    return "Attacker Victory";
  }
  if (outcome === "defender_victory") {
    return "Defender Victory";
  }
  if (outcome === "mutual_disengagement") {
    return "Mutual Disengagement";
  }
  return outcome.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function getBannerStyle(outcome: string): string {
  if (outcome.includes("victory") || outcome === "attacker_victory") {
    return "bg-[#5E8A5A]/20 border-[#5E8A5A]/40 text-[#254625]";
  }
  if (outcome.includes("disengagement")) {
    return "bg-[#46606E]/20 border-[#46606E]/40 text-[#2e4856]";
  }
  return "bg-[#785a00]/15 border-[#D2A94A]/40 text-[#785a00]";
}

interface VictorBannerProps {
  outcome: string;
}

function VictorBanner({ outcome }: VictorBannerProps) {
  const bannerText = formatOutcomeBanner(outcome);
  const colorClass = getBannerStyle(outcome);

  return (
    <div className={`p-4 rounded-xl border text-center shadow-inner ${colorClass}`}>
      <span className="material-symbols-outlined text-[32px] mb-1">military_tech</span>
      <h2 className="font-serif text-[24px] font-bold tracking-wide">
        {bannerText}
      </h2>
    </div>
  );
}

interface HostLossesComparisonProps {
  playerLosses: number;
  enemyStrength: StrengthInterval | null;
}

function formatEnemyStrength(strength: StrengthInterval | null): string {
  if (!strength) return "Unknown";
  return `${strength.minimum.toLocaleString()}–${strength.maximum.toLocaleString()}`;
}

function HostLossesComparison({ playerLosses, enemyStrength }: HostLossesComparisonProps) {
  return (
    <div className="strategy-stagger grid grid-cols-2 gap-3">
      <div className="strategy-rise p-3.5 rounded-xl bg-[#fffcf5] border border-[#3A3128]/15 text-center flex flex-col gap-1">
        <span className="text-[11px] uppercase tracking-wider font-bold text-[#42474b]">
          Total Host Losses
        </span>
        <span className="font-serif text-[24px] font-bold text-[#7c2820]">
          {playerLosses.toLocaleString()}
        </span>
        <span className="text-[11px] text-[#72787c]">Fallen & Dispersed</span>
      </div>
      <div className="strategy-rise p-3.5 rounded-xl bg-[#fffcf5] border border-[#3A3128]/15 text-center flex flex-col gap-1">
        <span className="text-[11px] uppercase tracking-wider font-bold text-[#42474b]">
          Enemy Host Remaining
        </span>
        <span className="font-serif text-[24px] font-bold text-[#5E8A5A]">
          {formatEnemyStrength(enemyStrength)}
        </span>
        <span className="text-[11px] text-[#72787c]">Estimated by outriders</span>
      </div>
    </div>
  );
}

interface CaptiveCardProps {
  captive: NobleCaptive;
}

function CaptiveCard({ captive }: CaptiveCardProps) {
  return (
    <div className="p-3.5 rounded-xl bg-[#fffcf5] border border-[#D2A94A]/40 flex flex-col gap-3 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#785a00] text-[20px]">person</span>
          <div>
            <h4 className="font-serif font-bold text-[15px] text-[#221A12]">{captive.name}</h4>
            <span className="text-[12px] text-[#72787c]">{captive.title}</span>
          </div>
        </div>
        <span className="text-[12px] font-bold text-[#785a00] bg-[#ebdcb9] px-2.5 py-0.5 rounded border border-[#D2A94A]/30">
          Ransom: {captive.ransomValueGold}g
        </span>
      </div>
      <p className="text-[12px] italic text-[#42474b]">
        Awaiting the sovereign's judgment. They will be brought before the throne when the turn
        ends.
      </p>
    </div>
  );
}

interface CaptivesPanelProps {
  captives: NobleCaptive[];
}

function CaptivesPanel({ captives }: CaptivesPanelProps) {
  if (captives.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[12px] font-serif font-bold text-[#785a00] uppercase tracking-wider">
        <span className="material-symbols-outlined text-[16px]">lock_person</span>
        Noble Captives Awaiting Judgment
      </div>
      <div className="flex flex-col gap-2">
        {captives.map((captive) => (
          <CaptiveCard key={captive.nobleId} captive={captive} />
        ))}
      </div>
    </div>
  );
}

export function BattleAftermathModal({
  isOpen = true,
  aftermath,
  outcome,
  totalHostLosses,
  enemyStrengthRemaining,
  nobleCaptives,
  onReturnToRealmMap,
}: BattleAftermathModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, isOpen);
  if (!isOpen) {
    return null;
  }

  const resolvedOutcome = aftermath?.outcome ?? outcome ?? "mutual_disengagement";
  const resolvedPlayerLosses = aftermath?.totalHostLosses ?? totalHostLosses ?? 0;
  const resolvedEnemyStrength = aftermath?.enemyStrengthRemaining ?? enemyStrengthRemaining ?? null;
  const resolvedCaptives = aftermath?.nobleCaptives ?? nobleCaptives ?? [];

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label="Battle aftermath"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#382f26]/60 backdrop-blur-sm"
    >
      <div className="strategy-rise w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#F7F0DC] shadow-2xl p-6 border-2 border-[#D2A94A]/60 flex flex-col gap-5 text-[#221A12]">
        <VictorBanner outcome={resolvedOutcome} />
        <HostLossesComparison
          playerLosses={resolvedPlayerLosses}
          enemyStrength={resolvedEnemyStrength}
        />
        <CaptivesPanel captives={resolvedCaptives} />
        <div className="flex justify-end pt-2 border-t border-[#D2A94A]/30">
          <button
            type="button"
            onClick={onReturnToRealmMap}
            className="px-6 py-2.5 rounded-xl bg-[#2e4856] hover:bg-[#46606E] text-white font-serif font-bold text-[14px] shadow-md cursor-pointer transition-colors"
          >
            Return to Realm Map
          </button>
        </div>
      </div>
    </div>
  );
}
