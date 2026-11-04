import type {
  ReservePolicyType,
  WithdrawalPolicyType,
} from "../../../types/simulation.types";
import type { StrategyInspectorAction } from "../../../types/strategyActions.types";

export interface ArmyPolicyPresetsProps {
  armyId: string;
  withdrawalPolicy?: WithdrawalPolicyType | null;
  reservePolicy?: ReservePolicyType | null;
  onAction?: (action: StrategyInspectorAction) => void;
}

const WITHDRAWAL_OPTIONS: { value: WithdrawalPolicyType; label: string }[] = [
  { value: "preserve", label: "Save the host" },
  { value: "balanced", label: "Balanced" },
  { value: "hold_at_cost", label: "Hold at any cost" },
];

const RESERVE_OPTIONS: { value: ReservePolicyType; label: string }[] = [
  { value: "conserve", label: "Conserve" },
  { value: "reinforce_on_pressure", label: "Reinforce under pressure" },
];

const SELECT_CLASS =
  "rounded border border-[#3A3128]/20 bg-[#fff8f4] px-1.5 py-1 text-xs font-semibold text-[#221A12]";

export function ArmyPolicyPresets({ armyId, withdrawalPolicy, reservePolicy, onAction }: ArmyPolicyPresetsProps) {
  return (
    <div className="flex flex-col gap-1.5 border-t border-[#72787C]/30 px-3 py-2">
      <span className="text-[10px] font-bold uppercase tracking-widest text-[#46606E]">
        Standing orders for the next battle
      </span>
      <label className="flex items-center justify-between gap-2 text-xs text-[#72787C]">
        If hard pressed
        <select
          className={SELECT_CLASS}
          value={withdrawalPolicy ?? "balanced"}
          onChange={(event) =>
            onAction?.({
              type: "set_army_policy",
              armyId,
              policy: { withdrawal_policy: event.target.value as WithdrawalPolicyType },
            })
          }
        >
          {WITHDRAWAL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="flex items-center justify-between gap-2 text-xs text-[#72787C]">
        Reserves
        <select
          className={SELECT_CLASS}
          value={reservePolicy ?? "conserve"}
          onChange={(event) =>
            onAction?.({
              type: "set_army_policy",
              armyId,
              policy: { reserve_policy: event.target.value as ReservePolicyType },
            })
          }
        >
          {RESERVE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
