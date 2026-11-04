import type { ReactNode } from "react";
import type { MissionTarget, OpponentView, ReconReport, StrengthInterval } from "../StrategyWarCouncil.types";

export interface EnemyCrestIntelProps {
  scoutedTurnText: string;
  opponent: OpponentView;
  canScout: boolean;
  isSending?: boolean;
  onOrderScout: (target: MissionTarget) => void;
}

interface FlankCardProps {
  min: number;
  max: number;
}

const SCOUT_TARGETS: Array<{ target: MissionTarget; label: string }> = [
  { target: "composition", label: "Scout composition" },
  { target: "reserves", label: "Scout reserves" },
  { target: "preparation", label: "Scout preparation" },
];

function describeReport(report: ReconReport): string {
  const range = `${report.strength.minimum.toLocaleString()}–${report.strength.maximum.toLocaleString()}`;
  const parts = [`Turn ${report.observed_turn}: ${report.target}`, `strength ${range}`];
  if (report.reserves) {
    parts.push(`reserves ${report.reserves.minimum.toLocaleString()}–${report.reserves.maximum.toLocaleString()}`);
  }
  if (report.composition) {
    const mix = Object.entries(report.composition)
      .map(([troop, count]) => `${count.toLocaleString()} ${troop.replace("_", "/")}`)
      .join(", ");
    parts.push(mix);
  }
  if (report.preparation_hint) parts.push(report.preparation_hint);
  parts.push(`${report.confidence} confidence`);
  return parts.join(" • ");
}

interface ScoutPanelProps {
  reports: ReconReport[];
  canScout: boolean;
  isSending: boolean;
  onOrderScout: (target: MissionTarget) => void;
}

function ScoutPanel({ reports, canScout, isSending, onOrderScout }: ScoutPanelProps) {
  return (
    <div className="w-full max-w-[680px] mb-2.5 p-2.5 rounded-xl bg-[#F7F0DC]/90 border border-[#3A3128]/15 flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider font-bold text-[#2e4856]">Send outriders</span>
        {SCOUT_TARGETS.map(({ target, label }) => (
          <button
            key={target}
            type="button"
            disabled={!canScout}
            aria-busy={isSending}
            onClick={() => onOrderScout(target)}
            className="px-2.5 py-1 rounded-lg bg-[#2e4856] text-white text-[11px] font-semibold cursor-pointer hover:bg-[#46606E] active:translate-y-px transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSending ? "Sending…" : label}
          </button>
        ))}
      </div>
      {reports.length === 0 ? (
        <p className="text-[11px] italic text-[#72787c]">No scouting reports yet.</p>
      ) : (
        <ul aria-live="polite" className="flex flex-col gap-1">
          {reports.map((report) => (
            <li key={report.id} className="strategy-rise text-[11px] text-[#221a12]">
              {describeReport(report)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function IntelBanner({ scoutedTurnText }: { scoutedTurnText: string }) {
  return (
    <div className="flex items-center gap-3 mb-2.5 px-3.5 py-1 rounded-full bg-[#f5e5d8]/90 backdrop-blur text-[12px] text-[#221a12] shadow-xs border border-[#3A3128]/10">
      <div className="flex items-center gap-1 text-[#2e4856]">
        <span className="material-symbols-outlined text-[15px]">visibility</span>
        <span className="font-semibold">{scoutedTurnText}</span>
      </div>
    </div>
  );
}

function latestReport(reports: ReconReport[], pick: (report: ReconReport) => boolean): ReconReport | null {
  const matching = reports.filter(pick);
  return matching.length ? matching[matching.length - 1]! : null;
}

function IntelCard({ title, icon, children }: { title: string; icon: string; children: ReactNode }) {
  return (
    <div className="relative p-2.5 rounded-xl bg-[#F7F0DC]/85 backdrop-blur-md shadow-xs flex flex-col gap-1 border border-[#3A3128]/15">
      <div className="flex items-center gap-1 text-[11px] font-bold text-[#2e4856]">
        <span className="material-symbols-outlined text-[14px]">{icon}</span>
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

function StrengthCard({ min, max }: FlankCardProps) {
  return (
    <IntelCard title="Enemy strength" icon="shield">
      <div className="text-[15px] font-extrabold font-serif text-[#221a12] leading-tight">
        {min.toLocaleString()}–{max.toLocaleString()} troops
      </div>
      <p className="text-[11px] text-[#72787c]">The widest range your scouts can give with what they have seen.</p>
    </IntelCard>
  );
}

function CompositionCard({ composition }: { composition: Record<string, number> | null }) {
  return (
    <IntelCard title="Troop mix" icon="groups">
      {composition ? (
        <ul className="text-[12px] text-[#221a12]">
          {Object.entries(composition).map(([troop, count]) => (
            <li key={troop}>
              {count.toLocaleString()} {troop.replace("_", "/")}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] italic text-[#72787c]">Unknown. Scout their composition.</p>
      )}
    </IntelCard>
  );
}

function ReservesCard({ reserves, hint }: { reserves: StrengthInterval | null; hint: string | null }) {
  return (
    <IntelCard title="Reserves and posture" icon="flag">
      <p className="text-[12px] text-[#221a12]">
        {reserves
          ? `Reserves ${reserves.minimum.toLocaleString()}–${reserves.maximum.toLocaleString()}`
          : "Reserves unknown. Scout their reserves."}
      </p>
      <p className="text-[12px] text-[#221a12]">
        {hint ? `Posture: ${hint}` : "Posture unknown. Scout their preparation."}
      </p>
    </IntelCard>
  );
}

export function EnemyCrestIntel({ scoutedTurnText, opponent, canScout, isSending = false, onOrderScout }: EnemyCrestIntelProps) {
  const composition = latestReport(opponent.reports, (report) => Boolean(report.composition))?.composition ?? null;
  const reserves = latestReport(opponent.reports, (report) => Boolean(report.reserves))?.reserves ?? null;
  const hint = latestReport(opponent.reports, (report) => Boolean(report.preparation_hint))?.preparation_hint ?? null;

  return (
    <div className="relative z-10 p-4 pt-3 flex flex-col items-center">
      <IntelBanner scoutedTurnText={scoutedTurnText} />
      <ScoutPanel reports={opponent.reports} canScout={canScout} isSending={isSending} onOrderScout={onOrderScout} />
      <div className="w-full max-w-[680px] grid grid-cols-1 md:grid-cols-3 gap-2.5 items-stretch">
        <StrengthCard min={opponent.strength.minimum} max={opponent.strength.maximum} />
        <CompositionCard composition={composition} />
        <ReservesCard reserves={reserves} hint={hint} />
      </div>
    </div>
  );
}
