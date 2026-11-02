import type { FormationType } from "../StrategyWarCouncil.types";
import { FormationSlotCard } from "./FormationSlotCard";

export interface PlayerFormationSlotsProps {
  formation: FormationType;
  anchorSlot: "left" | "center" | "right";
  onSelectSlot: (slot: "left" | "center" | "right") => void;
  troops: Record<string, number>;
  morale: number;
}

export function PlayerFormationSlots({
  formation,
  anchorSlot,
  onSelectSlot,
  troops,
  morale,
}: PlayerFormationSlotsProps) {
  const totalTroops = Object.values(troops).reduce((sum, n) => sum + n, 0);

  // Partition troops by formation preset (O12)
  let centerPct = 0.4;
  let flankPct = 0.3;
  if (formation === "defensive") {
    centerPct = 0.5;
    flankPct = 0.25;
  } else if (formation === "concentrated") {
    centerPct = 0.6;
    flankPct = 0.2;
  }

  const leftCount = Math.round(totalTroops * flankPct);
  const centerCount = Math.round(totalTroops * centerPct);
  const rightCount = Math.round(totalTroops * flankPct);

  return (
    <div className="w-full max-w-[660px] grid grid-cols-3 gap-3 items-end">
      <FormationSlotCard
        slot="left"
        title="Left Flank • Ashwood"
        unitName="Barrow Halberdiers"
        troopCountText={`${leftCount} Heavy Foot`}
        morale={morale}
        isAnchor={anchorSlot === "left"}
        onSelect={() => onSelectSlot("left")}
      />
      <FormationSlotCard
        slot="center"
        title="Center Vanguard • Ford"
        unitName="Valenreach Shieldwall"
        troopCountText={`${centerCount} Spearmen`}
        morale={morale}
        isAnchor={anchorSlot === "center"}
        onSelect={() => onSelectSlot("center")}
      />
      <FormationSlotCard
        slot="right"
        title="Right Flank • Mud Meadow"
        unitName="Silverwood Archers"
        troopCountText={`${rightCount} Longbows`}
        morale={morale}
        isAnchor={anchorSlot === "right"}
        onSelect={() => onSelectSlot("right")}
      />
    </div>
  );
}
