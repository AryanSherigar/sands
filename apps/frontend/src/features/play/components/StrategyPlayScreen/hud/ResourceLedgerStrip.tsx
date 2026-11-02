import type { FC } from "react";
import { IconCoin, IconShield, IconScale, IconFeather } from "@tabler/icons-react";
import { deriveDate } from "../../../lib/strategyClock";
import { deriveOrdersBudget } from "../../../lib/ordersBudget";
import { StatChip } from "./StatChip";
import type { ResourceLedgerStripProps } from "./ResourceLedgerStrip.types";

export const ResourceLedgerStrip: FC<ResourceLedgerStripProps> = ({ world, onOpenTreasury }) => {
  const faction = world?.my_faction;
  const clock = world?.clock;
  const date = clock ? deriveDate(clock) : null;
  const clockText = date ? `${date.year} · ${date.season}` : "";
  const manpower = (faction?.manpower ?? 0).toLocaleString();
  const budget = world ? deriveOrdersBudget(world) : null;
  const mandates = `${budget?.remaining ?? 0} / ${budget?.total ?? 0} Remaining`;
  const goldTooltip = onOpenTreasury
    ? "Wealth used to muster regiments and issue provincial decrees. Click to open treasury controls."
    : "Wealth used to muster regiments and issue provincial decrees.";
  const goldChip = (
    <StatChip
      icon={<IconCoin size={14} stroke={1.75} />}
      value={String(faction?.treasury ?? 0)}
      tooltipTitle="Gold Treasury"
      tooltipDesc={goldTooltip}
    />
  );

  return (
    <div className="flex max-w-full flex-wrap items-center gap-x-1.5 gap-y-1 p-1 px-2.5 rounded-2xl sm:rounded-full bg-[#F7F0DC]/95 backdrop-blur-xl border border-[#3A3128]/20 shadow-md">
      {onOpenTreasury ? (
        <button type="button" onClick={onOpenTreasury} aria-label="Open treasury" className="rounded-full">
          {goldChip}
        </button>
      ) : (
        goldChip
      )}
      <StatChip icon={<IconShield size={14} stroke={1.75} />} value={manpower} tooltipTitle="Manpower Reserves" tooltipDesc="Available levy pool that sustains forces and absorbs casualties." />
      <StatChip icon={<IconScale size={14} stroke={1.75} />} value={`+${faction?.stability ?? 0}`} tooltipTitle="Realm Stability" tooltipDesc="High stability prevents civil unrest and boosts provincial tax receipts." />
      <StatChip icon={<IconFeather size={14} stroke={1.75} />} value={mandates} tooltipTitle="Royal Mandates" tooltipDesc="Strategic actions remaining for this 2-month season." />
      <div className="px-2 py-0.5 rounded-full bg-[#F5E5D8] border border-[#3A3128]/10 text-[10px] text-[#42474B] font-medium">
        {clockText}
      </div>
    </div>
  );
};
