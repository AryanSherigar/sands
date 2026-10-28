import React from "react";
import { IconX } from "@tabler/icons-react";
import { ProvinceCharterView } from "./ProvinceCharterView";
import { ArmyRosterView } from "./ArmyRosterView";
import type { StrategyLeftInspectorProps } from "./StrategyLeftInspector.types";

const DRAWER_BASE_CLASS =
  "fixed top-16 left-4 z-40 w-[350px] bg-[#F7F0DC]/95 backdrop-blur-xl rounded-xl border border-[#3A3128]/20 shadow-2xl transition-all duration-300 ease-out overflow-hidden";

const getVisibilityClass = (isOpen: boolean): string =>
  isOpen
    ? "translate-x-0 opacity-100 pointer-events-auto"
    : "-translate-x-[110%] opacity-0 pointer-events-none";

interface CloseButtonProps {
  onClose: () => void;
}

const CloseButton: React.FC<CloseButtonProps> = ({ onClose }) => (
  <div className="flex justify-end p-2 pb-0">
    <button
      type="button"
      onClick={onClose}
      aria-label="Close inspector"
      className="text-[#72787C] hover:text-[#221A12] p-1 flex items-center justify-center cursor-pointer"
    >
      <IconX size={16} stroke={1.75} />
    </button>
  </div>
);

export const StrategyLeftInspector: React.FC<StrategyLeftInspectorProps> = (
  props,
) => {
  const { selectedEntity, region, army, world, onClose, onAction } = props;
  const isOpen = Boolean(selectedEntity);
  const hasRegion = selectedEntity?.type === "region" && Boolean(region);
  const hasArmy = selectedEntity?.type === "army" && Boolean(army);

  return (
    <aside className={`${DRAWER_BASE_CLASS} ${getVisibilityClass(isOpen)}`}>
      <CloseButton onClose={onClose} />
      {hasRegion && region ? (
        <ProvinceCharterView region={region} world={world} onAction={onAction} />
      ) : null}
      {hasArmy && army ? (
        <ArmyRosterView
          army={army}
          isOwnArmy={army.owner_id === world?.my_faction.id}
          onAction={onAction}
        />
      ) : null}
    </aside>
  );
};
