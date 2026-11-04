import type { DemandReply, PayLevel, SetArmyPolicyOrder, TroopType } from "./simulation.types";

export type StrategyInspectorAction =
  | { type: "levy"; regionId: string }
  | { type: "move"; armyId: string }
  | { type: "attack"; armyId: string }
  | { type: "besiege"; armyId: string }
  | { type: "halt"; armyId: string }
  | { type: "disband"; armyId: string }
  | { type: "set_army_policy"; armyId: string; policy: Pick<SetArmyPolicyOrder, "withdrawal_policy" | "reserve_policy"> }
  | { type: "split"; armyId: string; troops: Partial<Record<TroopType, number>> }
  | { type: "map_scout"; regionId: string }
  | { type: "fabricate_claim"; targetFactionId: string; regionId: string }
  | { type: "set_pay"; armyId: string; payLevel: PayLevel }
  | { type: "declare_war"; targetFactionId: string }
  | { type: "sue_peace"; warId: string }
  | { type: "send_envoy"; targetFactionId: string }
  | { type: "call_negotiation"; targetFactionId: string }
  | { type: "answer_call"; callId: string; isJoining: boolean }
  | { type: "answer_demand"; demandId: string; reply: DemandReply };
