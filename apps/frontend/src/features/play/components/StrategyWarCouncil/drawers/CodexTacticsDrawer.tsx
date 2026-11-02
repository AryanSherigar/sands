import { useRef } from "react";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { formatTerrainLabel, formatWeatherLabel } from "../../../lib/battleLabels";
import type { BattleView, StandingPlan, TacticType } from "../StrategyWarCouncil.types";

export interface CodexTacticsDrawerProps {
  isOpen: boolean;
  battle: BattleView;
  onClose: () => void;
}

const TACTIC_GLOSSES: Record<TacticType, string> = {
  hold: "Stand fast and make the enemy come to you.",
  hold_high_ground: "Stand fast on the best ground available.",
  press: "Drive forward and force the fighting.",
  flank: "Send part of the line round the enemy's side.",
  feigned_retreat: "Give ground on purpose to draw the enemy out of position.",
  forest_flank: "Strike from cover on forested ground.",
  night_attack: "Attack under cover of darkness.",
};

const RESERVE_POLICY_TEXT: Record<StandingPlan["reserve_policy"], string> = {
  conserve: "Keep reserves back until you commit them.",
  reinforce_on_pressure: "Feed reserves in when the line is under pressure.",
};

const SUPPLY_TEXT: Record<string, string> = {
  supplied: "Well supplied",
  strained: "Supply strained",
  isolated: "Cut off from supply",
};

function formatPlanValue(value: string): string {
  return value.replace(/_/g, " ");
}

function FieldConditions({ battle }: { battle: BattleView }) {
  const contingent = battle.own_contingent;
  const rows: Array<[string, string]> = [
    ["Terrain", formatTerrainLabel(battle.terrain)],
    ["Weather", formatWeatherLabel(battle.weather)],
  ];
  if (battle.frontage) rows.push(["Frontage", `${battle.frontage.toLocaleString()} troops can fight abreast`]);
  if (contingent) {
    rows.push(
      ["Supply", SUPPLY_TEXT[contingent.supply] ?? contingent.supply],
      ["Formation", formatPlanValue(contingent.plan.formation)],
      ["Tactic", formatPlanValue(contingent.plan.tactic)],
      ["Withdrawal", formatPlanValue(contingent.plan.withdrawal_policy)],
      ["Reserves", RESERVE_POLICY_TEXT[contingent.plan.reserve_policy]],
    );
  }
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-lg border border-[#3A3128]/10 bg-[#fff8f4] p-3 text-[12px]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="font-semibold text-[#2e4856]">{label}</dt>
          <dd className="capitalize text-[#42474b]">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function CodexTacticsDrawer({ isOpen, battle, onClose }: CodexTacticsDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, isOpen);
  useEscapeKey(isOpen, onClose);
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-[#382f26]/40 backdrop-blur-xs" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Codex of War and Terrain"
        className="strategy-slide-left relative z-10 flex h-full w-full max-w-md flex-col border-l border-[#3A3128]/20 bg-[#F7F0DC] shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-[#3A3128]/15 bg-[#fff8f4]/90 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[22px] text-[#2e4856]">menu_book</span>
            <h2 className="font-serif text-[20px] font-semibold text-[#2e4856]">Codex of War & Terrain</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close the codex"
            className="cursor-pointer rounded p-1 text-[#42474b] hover:bg-[#fbebde]"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5 text-[#221a12]">
          <p className="text-[12px] italic text-[#72787c]">
            General guidance only. The battle engine decides the real effects.
          </p>

          <section className="flex flex-col gap-2">
            <h3 className="font-serif text-[17px] font-semibold text-[#2e4856]">Conditions at this battle</h3>
            <FieldConditions battle={battle} />
          </section>

          <section className="flex flex-col gap-2">
            <h3 className="font-serif text-[17px] font-semibold text-[#2e4856]">Doctrines</h3>
            {(Object.entries(TACTIC_GLOSSES) as Array<[TacticType, string]>).map(([tactic, gloss]) => (
              <div key={tactic} className="rounded border border-[#3A3128]/10 bg-[#fff8f4]/80 p-2.5 text-[12px]">
                <p className="font-semibold capitalize text-[#2e4856]">{formatPlanValue(tactic)}</p>
                <p className="mt-0.5 text-[#42474b]">{gloss}</p>
              </div>
            ))}
          </section>
        </div>

        <div className="flex justify-end border-t border-[#3A3128]/15 bg-[#fff8f4]/60 p-4">
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer rounded-lg bg-[#2e4856] px-4 py-1.5 text-[13px] font-semibold text-white"
          >
            Done Reading
          </button>
        </div>
      </div>
    </div>
  );
}
