import React from "react";
import type { ArmyRosterViewProps } from "./ArmyRosterView.types";
import type { TroopType } from "../../../types/simulation.types";

const FALLBACK_COMMANDER = "Royal Host";

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
  onAction?: ArmyRosterViewProps["onAction"];
}

const ArmyActionButtons: React.FC<ActionsProps> = ({ armyId, onAction }) => {
  const handleMoveClick = (): void => {
    onAction?.({ type: "move", armyId });
  };
  const handleAttackClick = (): void => {
    onAction?.({ type: "attack", armyId });
  };
  const handleHaltClick = (): void => {
    onAction?.({ type: "halt", armyId });
  };

  return (
    <div className="p-3 border-t border-[#72787C]/30 grid grid-cols-3 gap-1.5">
      <ActionButton label="Move" isPrimary onClick={handleMoveClick} />
      <ActionButton label="Attack" onClick={handleAttackClick} />
      <ActionButton label="Halt" onClick={handleHaltClick} />
    </div>
  );
};

export const ArmyRosterView: React.FC<ArmyRosterViewProps> = ({
  army,
  isOwnArmy = true,
  onAction,
}) => (
  <div className="flex flex-col gap-3">
    <ArmyRosterHeader commanderName={army.commander_name} />
    {army.troops ? <ArmyTroopList troops={army.troops} /> : null}
    {isOwnArmy ? <ArmyActionButtons armyId={army.army_id} onAction={onAction} /> : null}
  </div>
);
