import React, { useState } from "react";
import { StrategyConfirmDialog } from "../ui/StrategyConfirmDialog";
import { ArmyPolicyPresets } from "./ArmyPolicyPresets";
import { SplitArmyForm } from "./SplitArmyForm";
import type { ArmyRosterViewProps } from "./ArmyRosterView.types";
import type { PayLevel, TroopType } from "../../../types/simulation.types";

const FALLBACK_COMMANDER = "Royal Host";

const PAY_LEVELS: { level: PayLevel; label: string }[] = [
  { level: "full", label: "Full Pay" },
  { level: "reduced", label: "Reduced Pay" },
];

interface HeaderProps {
  commanderName?: string | null;
}

const ArmyRosterHeader: React.FC<HeaderProps> = ({ commanderName }) => (
  <div className="p-3 bg-[#F5E5D8]/60 border-b border-[#72787C]/30 flex flex-col gap-1">
    <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-widest">
      Command Host
    </span>
    <h2 className="text-xl font-bold font-serif text-[#221A12]">
      {commanderName ?? FALLBACK_COMMANDER}
    </h2>
  </div>
);

interface TroopListProps {
  troops: Partial<Record<TroopType, number>>;
}

const ArmyTroopList: React.FC<TroopListProps> = ({ troops }) => (
  <div className="p-3 flex flex-col gap-1.5">
    {Object.entries(troops).map(([troopType, count]) => (
      <div key={troopType} className="flex justify-between text-xs">
        <span className="text-[#72787C] capitalize">{troopType.replace(/_/g, " ")}</span>
        <span className="font-bold font-mono text-[#221A12]">{count.toLocaleString()}</span>
      </div>
    ))}
  </div>
);

interface PayToggleProps {
  armyId: string;
  currentPayLevel: PayLevel;
  onAction?: ArmyRosterViewProps["onAction"];
}

const PayToggle: React.FC<PayToggleProps> = ({ armyId, currentPayLevel, onAction }) => {
  const handleClick = (level: PayLevel): void => {
    if (level === currentPayLevel) return;
    onAction?.({ type: "set_pay", armyId, payLevel: level });
  };

  return (
    <div className="px-3 pb-2 flex gap-1">
      {PAY_LEVELS.map(({ level, label }) => {
        const isActive = level === currentPayLevel;
        return (
          <button
            key={level}
            type="button"
            aria-pressed={isActive}
            onClick={() => handleClick(level)}
            className={`flex-1 py-1 rounded text-xs font-bold transition-colors ${
              isActive
                ? "bg-[#46606E] text-white"
                : "bg-[#F5E5D8] border border-[#3A3128]/15 text-[#221A12] hover:bg-[#F0E0D2]"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

interface ActionButtonProps {
  label: string;
  isPrimary?: boolean;
  onClick: () => void;
}

const ActionButton: React.FC<ActionButtonProps> = ({ label, isPrimary, onClick }) => (
  <button
    type="button"
    className={`py-1.5 rounded text-xs font-bold ${
      isPrimary
        ? "bg-[#46606E] text-white hover:opacity-90"
        : "bg-[#F5E5D8] border border-[#3A3128]/15 text-[#221A12] hover:bg-[#F0E0D2]"
    }`}
    onClick={onClick}
  >
    {label}
  </button>
);

interface ActionsProps {
  armyId: string;
  troops?: Partial<Record<TroopType, number>> | null;
  canBesiege?: boolean;
  onAction?: ArmyRosterViewProps["onAction"];
}

const ArmyActionButtons: React.FC<ActionsProps> = ({ armyId, troops, canBesiege, onAction }) => {
  const handleMoveClick = (): void => {
    onAction?.({ type: "move", armyId });
  };
  const handleAttackClick = (): void => {
    onAction?.({ type: "attack", armyId });
  };
  const handleHaltClick = (): void => {
    onAction?.({ type: "halt", armyId });
  };
  const handleBesiegeClick = (): void => {
    onAction?.({ type: "besiege", armyId });
  };

  const [isSplitting, setIsSplitting] = useState(false);
  const [isConfirmingDisband, setIsConfirmingDisband] = useState(false);
  const handleConfirmDisband = (): void => {
    setIsConfirmingDisband(false);
    onAction?.({ type: "disband", armyId });
  };

  return (
    <div className="p-3 border-t border-[#72787C]/30 grid grid-cols-3 gap-1.5">
      <ActionButton label="Move" isPrimary onClick={handleMoveClick} />
      <ActionButton label="Attack" onClick={handleAttackClick} />
      {canBesiege ? <ActionButton label="Besiege" onClick={handleBesiegeClick} /> : null}
      <ActionButton label="Halt" onClick={handleHaltClick} />
      {troops ? <ActionButton label="Split" onClick={() => setIsSplitting(true)} /> : null}
      <ActionButton label="Disband" onClick={() => setIsConfirmingDisband(true)} />
      {isSplitting && troops ? (
        <SplitArmyForm
          troops={troops}
          onSubmit={(detachment) => {
            setIsSplitting(false);
            onAction?.({ type: "split", armyId, troops: detachment });
          }}
          onCancel={() => setIsSplitting(false)}
        />
      ) : null}
      <StrategyConfirmDialog
        isOpen={isConfirmingDisband}
        title="Disband this army?"
        message="The army is dissolved and its troops leave your service. This cannot be undone."
        confirmLabel="Disband"
        onConfirm={handleConfirmDisband}
        onCancel={() => setIsConfirmingDisband(false)}
      />
    </div>
  );
};

export const ArmyRosterView: React.FC<ArmyRosterViewProps> = ({
  army,
  isOwnArmy = true,
  isAtWar = false,
  canBesiege = false,
  onAction,
}) => (
  <div className="flex flex-col gap-3">
    <ArmyRosterHeader commanderName={army.commander_name} />
    {army.troops ? <ArmyTroopList troops={army.troops} /> : null}
    {isOwnArmy ? (
      <PayToggle
        armyId={army.army_id}
        currentPayLevel={army.pay_level ?? "full"}
        onAction={onAction}
      />
    ) : null}
    {isOwnArmy ? (
      <ArmyPolicyPresets
        armyId={army.army_id}
        withdrawalPolicy={army.withdrawal_policy}
        reservePolicy={army.reserve_policy}
        onAction={onAction}
      />
    ) : null}
    {isOwnArmy ? (
      <ArmyActionButtons armyId={army.army_id} troops={army.troops} canBesiege={canBesiege} onAction={onAction} />
    ) : null}
    {!isOwnArmy && !isAtWar && army.owner_id ? (
      <div className="p-3 border-t border-[#72787C]/30 grid grid-cols-1 gap-1.5">
        <button
          type="button"
          className="py-1.5 px-2 rounded bg-[#A8483E] text-white text-xs font-bold hover:opacity-90 cursor-pointer"
          onClick={() => onAction?.({ type: "declare_war", targetFactionId: army.owner_id })}
        >
          Declare War
        </button>
      </div>
    ) : null}
  </div>
);
