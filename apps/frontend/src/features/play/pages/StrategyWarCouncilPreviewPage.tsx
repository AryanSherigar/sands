import { useNavigate } from "react-router-dom";
import { StrategyWarCouncilScreen } from "../components/StrategyWarCouncil";
import type { BattleView } from "../components/StrategyWarCouncil/StrategyWarCouncil.types";

const MOCK_PREVIEW_BATTLE: BattleView = {
  id: "battle-ashford-ridge",
  region_id: "ashford_ford",
  status: "awaiting_commands",
  outcome: null,
  current_turn: 1,
  exchanges_used: 0,
  total_exchanges: 4,
  is_big: true,
  control_mode: "player",
  terrain: "hills",
  weather: "rain",
  command_cost: 0,
  own_contingent: {
    faction_id: "valenreach",
    army_ids: ["army-1"],
    troops: {
      infantry: 1400,
      cavalry: 300,
      archers_siege: 650,
    },
    morale: 92,
    fatigue: 15,
    plan: {
      formation: "defensive",
      tactic: "hold",
      withdrawal_policy: "balanced",
      reserve_policy: "conserve",
    },
    supply: "supplied",
    status: "fighting",
  },
  opponents: [
    {
      faction_id: "ironmark",
      strength: { minimum: 1200, maximum: 1600 },
      reports: [],
    },
  ],
  legal_commands: ["set_plan", "reconnoitre", "withdraw", "surrender", "commit_reserves"],
};

export function StrategyWarCouncilPreviewPage() {
  const navigate = useNavigate();

  return (
    <StrategyWarCouncilScreen
      playthroughId="preview-pt"
      battleId="battle-ashford-ridge"
      regionNames={{ ashford_ford: "Ashford Ridge", "reg-dunmere": "Ashford Ridge" }}
      world={{ rivals: [], armies: [] }}
      initialBattle={MOCK_PREVIEW_BATTLE}
      onReturnToMap={() => {
        navigate("/play/strategy-preview");
      }}
    />
  );
}
