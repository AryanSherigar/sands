import type { FC } from "react";
import { IconCrown } from "@tabler/icons-react";
import type { SovereignBadgeProps } from "./SovereignBadge.types";

export const SovereignBadge: FC<SovereignBadgeProps> = ({
  name = "Sovereign",
  title = "Crown of the Realm",
}) => (
  <div className="pointer-events-auto flex items-center gap-2 p-1.5 pr-3.5 rounded-full bg-[#F7F0DC]/95 backdrop-blur-xl border border-[#3A3128]/20 shadow-md">
    <div className="w-8 h-8 rounded-full bg-[#46606E] text-white flex items-center justify-center">
      <IconCrown size={18} stroke={1.75} />
    </div>
    <div className="flex flex-col leading-tight">
      <span className="text-xs font-bold text-[#221A12]">{name}</span>
      <span className="text-[9px] text-[#72787C] uppercase tracking-wider">
        {title}
      </span>
    </div>
  </div>
);
