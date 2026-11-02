import type {
  WardConfig,
  WardIdentifier,
} from "../StrategyWarCouncil.types";

const createLeftWard = (): WardConfig => ({
  ward: "left",
  title: "Left Ward (Vanguard)",
  stance: "hold",
  isAnchor: false,
  ranks: [
    {
      id: "c-left-front",
      troopType: "infantry",
      name: "Vanguard Spearmen",
      count: 500,
      rankOrder: "front",
      tacticalRole: "Locks shields, braces against flank charges",
    },
    {
      id: "c-left-middle",
      troopType: "archers_siege",
      name: "Auxiliary Skirmishers",
      count: 200,
      rankOrder: "middle",
      tacticalRole: "Harasses approaching vanguard",
    },
    {
      id: "c-left-rear",
      troopType: "cavalry",
      name: "Outrider Horse",
      count: 100,
      rankOrder: "rear",
      tacticalRole: "Screens left flank and pursues broken foes",
    },
  ],
});

const createCenterWard = (): WardConfig => ({
  ward: "center",
  title: "Center (Main Battle)",
  stance: "hold",
  isAnchor: true,
  ranks: [
    {
      id: "c-center-front",
      troopType: "infantry",
      name: "Shieldwall Spearmen",
      count: 600,
      rankOrder: "front",
      tacticalRole: "Locks shields and braces against shock charges",
    },
    {
      id: "c-center-middle",
      troopType: "archers_siege",
      name: "Longbowmen",
      count: 400,
      rankOrder: "middle",
      tacticalRole: "Volley fire into attacking center",
    },
    {
      id: "c-center-rear",
      troopType: "cavalry",
      name: "Armored Knights",
      count: 200,
      rankOrder: "rear",
      tacticalRole: "Shock reserve to exploit breaches",
    },
  ],
});

const createRightWard = (): WardConfig => ({
  ward: "right",
  title: "Right Ward (Rearguard)",
  stance: "hold",
  isAnchor: false,
  ranks: [
    {
      id: "c-right-front",
      troopType: "infantry",
      name: "Line Footmen",
      count: 400,
      rankOrder: "front",
      tacticalRole: "Anchors right slope and checks skirmishers",
    },
    {
      id: "c-right-middle",
      troopType: "archers_siege",
      name: "Crossbowmen",
      count: 150,
      rankOrder: "middle",
      tacticalRole: "Point-blank armor penetration",
    },
    {
      id: "c-right-rear",
      troopType: "cavalry",
      name: "Light Horse",
      count: 100,
      rankOrder: "rear",
      tacticalRole: "Watches the right perimeter",
    },
  ],
});

export const buildDefaultWards = (): Record<WardIdentifier, WardConfig> => ({
  left: createLeftWard(),
  center: createCenterWard(),
  right: createRightWard(),
});
