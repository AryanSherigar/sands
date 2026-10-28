import React from "react";
import { IconFlame } from "@tabler/icons-react";
import type { CrisisAlertPinProps } from "../StrategyMap.types";

export const CrisisAlertPin: React.FC<CrisisAlertPinProps> = ({
  coords,
  label,
}) => (
  <div
    style={{ left: `${coords.x}px`, top: `${coords.y}px` }}
    className="absolute -translate-x-1/2 -translate-y-1/2 -mt-6 z-25 flex items-center gap-1 bg-[#A8483E] text-white px-2 py-0.5 rounded-full shadow-md text-[10px] font-bold animate-pulse"
  >
    <IconFlame size={12} stroke={2} />
    <span>{label}</span>
  </div>
);
