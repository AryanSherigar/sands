export type StrategyInspectorAction =
  | { type: "levy"; regionId: string }
  | { type: "move"; armyId: string }
  | { type: "attack"; armyId: string }
  | { type: "halt"; armyId: string };
