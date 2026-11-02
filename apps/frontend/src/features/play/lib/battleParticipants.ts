import type { BattleView } from "../components/StrategyWarCouncil/StrategyWarCouncil.types";
import type { CampaignWorldView } from "../types/simulation.types";

const PLAYER_FACTION_FALLBACK = "Your realm";
const ENEMY_FACTION_FALLBACK = "The enemy";

export interface BattleCommander {
  name: string;
  portraitUrl?: string;
}

export interface BattleParticipants {
  playerFactionName: string;
  enemyFactionName: string;
  playerCommander: BattleCommander | null;
  enemyCommander: BattleCommander | null;
}

type ParticipantWorld = Pick<CampaignWorldView, "rivals" | "armies">;

function findPlayerCommander(
  battle: BattleView,
  world: ParticipantWorld,
): BattleCommander | null {
  const armyIds = new Set(battle.own_contingent?.army_ids ?? []);
  const army = world.armies.find((candidate) => armyIds.has(candidate.army_id) && candidate.commander_name);
  return army?.commander_name ? { name: army.commander_name } : null;
}

export function buildBattleParticipants(
  battle: BattleView,
  world: ParticipantWorld,
): BattleParticipants {
  const rival = world.rivals.find((candidate) => candidate.faction_id === battle.opponents[0]?.faction_id);
  const hasLeader = Boolean(rival?.leader_name);
  return {
    playerFactionName: PLAYER_FACTION_FALLBACK,
    enemyFactionName: rival?.name ?? ENEMY_FACTION_FALLBACK,
    playerCommander: findPlayerCommander(battle, world),
    enemyCommander: hasLeader
      ? { name: rival?.leader_name ?? "", portraitUrl: rival?.avatar_url ?? undefined }
      : null,
  };
}
