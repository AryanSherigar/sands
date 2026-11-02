import type { MissionTarget, OpponentView, ReconReport } from "../StrategyWarCouncil.types";
import { IconShield } from "@tabler/icons-react";

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
      <span className="text-[#c2c7cb]">•</span>
      <div className="flex items-center gap-1.5 text-[#42474b] text-[11px]">
        <span className="inline-block w-2 h-2 rounded-full bg-[#5E8A5A]" />
        <span>Wing cards below are illustrative; only the total strength is real</span>
      </div>
    </div>
  );
}

function LeftFlankCard({ min, max }: FlankCardProps) {
  return (
    <div className="enemy-wing-box relative p-2.5 rounded-xl bg-[#F7F0DC]/85 backdrop-blur-md shadow-xs flex flex-col justify-between border border-[#3A3128]/15 group">
      <div className="flex items-center justify-between text-[11px] font-bold">
        <span className="text-[#2e4856]">
          Enemy Left Wing (Illustrative)
        </span>
        <span className="text-[#46606E] flex items-center gap-0.5 text-[10px]">
          <span className="material-symbols-outlined text-[12px]">search</span> Outrider Report
        </span>
      </div>
      <div className="my-1">
        <div className="text-[15px] font-extrabold font-serif text-[#221a12] leading-tight">
          ~{min.toLocaleString()}–{max.toLocaleString()} horse & skirmishers estimated
        </div>
        <div className="flex items-center gap-1 text-[11px] text-[#46606E] font-semibold mt-0.5">
          <IconShield size={12} aria-hidden="true" />
          Spearmen & Pavisiers • Banner of Lord Morcar
        </div>
      </div>
      <div className="text-[10px] italic text-[#555] bg-[#fff8f4]/60 p-1 rounded border border-[#3A3128]/5">
        &ldquo;Ranks marshalled 8 deep behind willow copse.&rdquo;
      </div>
    </div>
  );
}

function CenterCommanderCard() {
  return (
    <div className="relative p-2.5 rounded-xl bg-[#f5e5d8]/95 backdrop-blur-md shadow-sm flex flex-col justify-between border-2 border-[#A8483E] text-center">
      <div>
        <div className="flex items-center justify-center gap-1 text-[#A8483E] text-[11px] font-bold uppercase tracking-wider mb-0.5">
          <span className="material-symbols-outlined text-[14px]">shield</span>
          <span>Enemy Center (Illustrative)</span>
        </div>
        <div className="text-[17px] font-extrabold font-serif text-[#A8483E] leading-tight">
          ~1,300 – 1,500 Armored Foot
        </div>
        <div className="text-[11px] text-[#221a12] font-semibold mt-0.5">
          Shock Lances in Front Rank • Poised for Immediate Charge
        </div>
      </div>
      <div className="text-[10px] italic text-[#6B5E4F] bg-[#fff8f4]/70 p-1 rounded mt-1 border border-[#A8483E]/10">
        &ldquo;Ironclad vanguard locked shoulder-to-shoulder on the crest slope.&rdquo;
      </div>
    </div>
  );
}

function RightFlankCard() {
  return (
    <div className="enemy-wing-box relative p-2.5 rounded-xl bg-[#DCE7EA]/60 backdrop-blur-md shadow-xs flex flex-col justify-between border border-dashed border-[#A0B2B6] group">
      <div className="flex items-center justify-between text-[11px] font-bold">
        <span className="text-[#42474b]">Enemy Right Wing (Illustrative)</span>
        <span className="text-[#72787C] flex items-center gap-0.5 text-[10px]">
          <span className="material-symbols-outlined text-[12px]">cloud</span> Veiled Mist
        </span>
      </div>
      <div className="my-1">
        <div className="text-[15px] font-bold font-serif text-[#72787c] leading-tight">
          ~800 – 1,600
        </div>
        <div className="text-[11px] text-[#72787c] font-medium mt-0.5">
          Mounted banners glimpsed through tree line
        </div>
      </div>
      <div className="text-[10px] italic text-[#666] bg-[#fff8f4]/50 p-1 rounded border border-[#3A3128]/5">
        &ldquo;Dust clouds suggest horse forming behind eastern rise.&rdquo;
      </div>
    </div>
  );
}

export function EnemyCrestIntel({ scoutedTurnText, opponent, canScout, isSending = false, onOrderScout }: EnemyCrestIntelProps) {
  const min = opponent.strength.minimum;
  const max = opponent.strength.maximum;

  return (
    <div className="relative z-10 p-4 pt-3 flex flex-col items-center">
      <IntelBanner scoutedTurnText={scoutedTurnText} />
      <ScoutPanel reports={opponent.reports} canScout={canScout} isSending={isSending} onOrderScout={onOrderScout} />
      <div className="w-full max-w-[680px] grid grid-cols-1 md:grid-cols-3 gap-2.5 items-stretch">
        <LeftFlankCard min={min} max={max} />
        <CenterCommanderCard />
        <RightFlankCard />
      </div>
    </div>
  );
}
